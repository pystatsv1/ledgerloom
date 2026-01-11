from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ledgerloom.ingest.csv_journal_entries import (
    ingest_journal_entries_csv,
    staging_postings_from_journal_entries_csv,
)


def _write_csv(path: Path, text: str) -> None:
    # Enforce LF newlines in test fixtures (Windows-safe determinism).
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def test_ingest_journal_entries_happy_path(tmp_path: Path) -> None:
    csv_path = tmp_path / "journal.csv"
    _write_csv(
        csv_path,
        """entry_id,date,narration,account,debit,credit
T001,2026-01-01,Owner investment,Assets:Cash,10000,
T001,2026-01-01,Owner investment,Equity:Owner Capital,,10000
T002,2026-01-02,Buy equipment,Assets:Equipment,3000,
T002,2026-01-02,Buy equipment,Assets:Cash,,3000
""",
    )

    result = ingest_journal_entries_csv(csv_path, source_name="Journal Entries")
    assert result.issues == []
    assert len(result.entries) == 2

    e0 = result.entries[0]
    assert e0.dt.isoformat() == "2026-01-01"
    assert e0.narration == "Owner investment"
    assert e0.meta["entry_id"] == "journal:Journal_Entries:journal.csv:T001"
    p0, p1 = e0.postings
    assert p0.account == "Assets:Cash"
    assert p0.debit == Decimal("10000.00")
    assert p1.account == "Equity:Owner Capital"
    assert p1.credit == Decimal("10000.00")

    e1 = result.entries[1]
    assert e1.dt.isoformat() == "2026-01-02"
    assert e1.meta["entry_id"] == "journal:Journal_Entries:journal.csv:T002"
    p0, p1 = e1.postings
    assert p0.account == "Assets:Equipment"
    assert p0.debit == Decimal("3000.00")
    assert p1.account == "Assets:Cash"
    assert p1.credit == Decimal("3000.00")


def test_ingest_journal_entries_unbalanced_entry_strict_false(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    _write_csv(
        csv_path,
        """entry_id,date,narration,account,debit,credit
T999,2026-01-05,Bad entry,Assets:Cash,10,
T999,2026-01-05,Bad entry,Revenue:Sales,,9
""",
    )

    result = ingest_journal_entries_csv(csv_path, source_name="Journal Entries", strict=False)
    assert result.entries == []
    assert any(i.code == "unbalanced_entry" for i in result.issues)


def test_journal_entries_staging_postings(tmp_path: Path) -> None:
    csv_path = tmp_path / "adjustments.csv"
    csv_path.write_text(
        "\n".join(
            [
                "entry_id,date,narration,account,debit,credit",
                "A1,2026-01-31,Adjusting entry,Expenses:Supplies,\"1,234.50\",",
                "A1,2026-01-31,Adjusting entry,Assets:Supplies,,\"(1,234.50)\"",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    rows, issues = staging_postings_from_journal_entries_csv(
        csv_path,
        source_name="adjustments",
        source_path="inputs/2026-01/adjustments.csv",
        entry_kind="adjustment",
        date_format="%Y-%m-%d",
        thousands_sep=",",
        decimal_sep=".",
        entry_id_col="entry_id",
        date_col="date",
        narration_col="narration",
        account_col="account",
        debit_col="debit",
        credit_col="credit",
    )

    assert issues == []
    assert [r["source_row_number"] for r in rows] == [1, 2]
    assert rows[0]["date"] == "2026-01-31"
    assert rows[0]["debit"] == "1234.50"
    assert rows[0]["credit"] == ""
    assert rows[1]["debit"] == ""
    assert rows[1]["credit"] == "-1234.50"
    assert {r["entry_kind"] for r in rows} == {"adjustment"}

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ledgerloom.ingest.csv_journal_entries import ingest_journal_entries_csv


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

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ledgerloom.ingest.csv_bank_feed import ingest_bank_feed_csv
from ledgerloom.project.config import BankFeedColumns, BankFeedSource


def _write_csv(path: Path, text: str) -> None:
    # Enforce LF newlines in test fixtures (Windows-safe determinism).
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def test_ingest_bank_feed_us_format(tmp_path: Path) -> None:
    csv_path = tmp_path / "bank.csv"
    _write_csv(
        csv_path,
        """Posting Date,Description,Amount
01/02/2026,Starbucks,-5.67
01/03/2026,Salary,1000.00
""",
    )

    source = BankFeedSource(
        name="Chase Checking",
        file_pattern=str(csv_path),
        default_account="Assets:US:Chase:Checking",
        columns=BankFeedColumns(date="Posting Date", description="Description", amount="Amount"),
        date_format="%m/%d/%Y",
        amount_thousands_sep=",",
        amount_decimal_sep=".",
        invert_amount_sign=False,
        suspense_account="Expenses:Uncategorized",
        rules=[
            {"pattern": "Starbucks", "account": "Expenses:Meals", "narration": "Coffee"},
            {"pattern": "Salary", "account": "Revenue:Salary"},
        ],
    )

    result = ingest_bank_feed_csv(csv_path, source)
    assert result.issues == []
    assert len(result.entries) == 2

    e0 = result.entries[0]
    assert e0.dt.isoformat() == "2026-01-02"
    assert e0.narration == "Coffee"
    assert e0.meta["entry_id"] == "bank:Chase_Checking:bank.csv:1"

    # Outflow: credit bank, debit expense
    p0, p1 = e0.postings
    assert p0.account == "Assets:US:Chase:Checking"
    assert p0.credit == Decimal("5.67")
    assert p0.debit == Decimal("0")
    assert p1.account == "Expenses:Meals"
    assert p1.debit == Decimal("5.67")
    assert p1.credit == Decimal("0")

    e1 = result.entries[1]
    assert e1.dt.isoformat() == "2026-01-03"
    assert e1.meta["entry_id"] == "bank:Chase_Checking:bank.csv:2"

    # Inflow: debit bank, credit revenue
    p0, p1 = e1.postings
    assert p0.account == "Assets:US:Chase:Checking"
    assert p0.debit == Decimal("1000.00")
    assert p1.account == "Revenue:Salary"
    assert p1.credit == Decimal("1000.00")


def test_ingest_bank_feed_eu_format(tmp_path: Path) -> None:
    csv_path = tmp_path / "eu.csv"
    _write_csv(
        csv_path,
        """Dato,Tekst,Beløb
31.01.2026,Adobe Creative Cloud,"1.234,56"
""",
    )

    source = BankFeedSource(
        name="EU Bank",
        file_pattern=str(csv_path),
        default_account="Assets:EU:Bank",
        columns=BankFeedColumns(date="Dato", description="Tekst", amount="Beløb"),
        date_format="%d.%m.%Y",
        amount_thousands_sep=".",
        amount_decimal_sep=",",
        invert_amount_sign=False,
        suspense_account="Expenses:Uncategorized",
        rules=[{"pattern": "Adobe", "account": "Expenses:Software"}],
    )

    result = ingest_bank_feed_csv(csv_path, source)
    assert result.issues == []
    assert len(result.entries) == 1

    e = result.entries[0]
    assert e.dt.isoformat() == "2026-01-31"
    # Positive amount => inflow: debit bank, credit target (even if the target
    # is an expense account in this tiny test).
    assert e.postings[0].debit == Decimal("1234.56")
    assert e.postings[1].credit == Decimal("1234.56")
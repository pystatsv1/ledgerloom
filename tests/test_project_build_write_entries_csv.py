from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.project.build import _write_entries_csv
from ledgerloom.project.paths import run_layout


def test_write_entries_csv_writes_canonical_rows(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)

    entries = [
        Entry(
            dt=date(2026, 1, 1),
            narration="Cash sale",
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("100"), credit=Decimal("0")),
                Posting(account="Revenue:Sales", debit=Decimal("0"), credit=Decimal("100")),
            ],
            meta={
                "entry_id": "journal:demo:1",
                "entry_kind": "journal",
                "source_name": "demo",
                "source_file": "bank.csv",
                "source_row_numbers": "1",
            },
        ),
        Entry(
            dt=date(2026, 1, 2),
            narration="Supplies",
            postings=[
                Posting(account="Expenses:Supplies", debit=Decimal("5.5"), credit=Decimal("0")),
                Posting(account="Assets:Cash", debit=Decimal("0"), credit=Decimal("5.5")),
            ],
            meta={"entry_id": "journal:demo:2", "entry_kind": "journal"},
        ),
    ]

    out_path = _write_entries_csv(entries=entries, run_root=run_root)
    assert out_path.exists()

    layout = run_layout(run_root)
    assert out_path == layout.artifacts_dir / "entries.csv"

    df = pd.read_csv(out_path, keep_default_na=False, dtype=str)
    assert list(df.columns) == [
        "entry_id",
        "date",
        "narration",
        "entry_kind",
        "line_no",
        "account",
        "debit",
        "credit",
        "source_name",
        "source_file",
        "source_row_numbers",
    ]

    rows = df.to_dict(orient="records")
    assert rows == [
        {
            "entry_id": "journal:demo:1",
            "date": "2026-01-01",
            "narration": "Cash sale",
            "entry_kind": "journal",
            "line_no": "1",
            "account": "Assets:Cash",
            "debit": "100",
            "credit": "0",
            "source_name": "demo",
            "source_file": "bank.csv",
            "source_row_numbers": "1",
        },
        {
            "entry_id": "journal:demo:1",
            "date": "2026-01-01",
            "narration": "Cash sale",
            "entry_kind": "journal",
            "line_no": "2",
            "account": "Revenue:Sales",
            "debit": "0",
            "credit": "100",
            "source_name": "demo",
            "source_file": "bank.csv",
            "source_row_numbers": "1",
        },
        {
            "entry_id": "journal:demo:2",
            "date": "2026-01-02",
            "narration": "Supplies",
            "entry_kind": "journal",
            "line_no": "1",
            "account": "Expenses:Supplies",
            "debit": "5.5",
            "credit": "0",
            "source_name": "",
            "source_file": "",
            "source_row_numbers": "",
        },
        {
            "entry_id": "journal:demo:2",
            "date": "2026-01-02",
            "narration": "Supplies",
            "entry_kind": "journal",
            "line_no": "2",
            "account": "Assets:Cash",
            "debit": "0",
            "credit": "5.5",
            "source_name": "",
            "source_file": "",
            "source_row_numbers": "",
        },
    ]

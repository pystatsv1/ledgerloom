from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerloom.cli import main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_cli_check_v2_multisource_writes_staging_postings_for_both_sources(tmp_path: Path) -> None:
    project_root = tmp_path / "demo_books"
    (project_root / "config").mkdir(parents=True, exist_ok=True)
    (project_root / "inputs" / "2026-01").mkdir(parents=True, exist_ok=True)

    _write(
        project_root / "config" / "chart_of_accounts.yaml",
        """\
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Cash
    name: Cash
    type: asset
  - code: Expenses:Meals
    name: Meals
    type: expense
  - code: Expenses:Uncategorized
    name: Uncategorized
    type: expense
""",
    )

    _write(
        project_root / "ledgerloom.yaml",
        """\
schema_id: ledgerloom.project_config.v2
project:
  name: Demo Books
  period: 2026-01
  currency: USD
chart_of_accounts: config/chart_of_accounts.yaml
strict_unmapped: false
sources:
  - source_type: bank_feed.v1
    name: Checking
    file_pattern: bank.csv
    default_account: Assets:Cash
    columns:
      date: Date
      description: Description
      amount: Amount
    date_format: "%m/%d/%Y"
    suspense_account: Expenses:Uncategorized
    rules:
      - pattern: "(?i)coffee"
        account: Expenses:Meals
  - source_type: journal_entries.v1
    name: Adjustments
    file_pattern: adjustments.csv
    entry_kind: adjustment
    columns:
      entry_id: entry_id
      date: date
      narration: narration
      account: account
      debit: debit
      credit: credit
    date_format: "%Y-%m-%d"
outputs:
  root: outputs
""",
    )

    _write(
        project_root / "inputs" / "2026-01" / "bank.csv",
        """\
Date,Description,Amount
01/02/2026,Coffee,-4.50
""",
    )

    # One balanced entry_id with two posting lines.
    _write(
        project_root / "inputs" / "2026-01" / "adjustments.csv",
        """\
entry_id,date,narration,account,debit,credit
A1,2026-01-31,Adjust coffee,Expenses:Meals,4.50,
A1,2026-01-31,Adjust coffee,Assets:Cash,,4.50
""",
    )

    outdir = project_root / "_out_check"
    rc = main(["check", "--project", str(project_root), "--outdir", str(outdir)])
    assert rc == 0

    staging = pd.read_csv(outdir / "staging_postings.csv")
    assert {"Checking", "Adjustments"} <= set(staging["source_name"].tolist())

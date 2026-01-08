from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerloom.__main__ import main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_cli_check_writes_artifacts_and_keeps_row_numbers(tmp_path: Path) -> None:
    project_root = tmp_path

    # Minimal project config.
    _write(
        project_root / "ledgerloom.yaml",
        """\
schema_id: ledgerloom.project_config.v1
project:
  name: Demo Books
  period: 2026-01
  currency: USD
chart_of_accounts: config/chart_of_accounts.yaml
sources:
  - source_type: bank_feed.v1
    name: Checking
    file_pattern: "*.csv"
    default_account: Assets:Cash
    columns:
      date: Date
      description: Description
      amount: Amount
    date_format: "%m/%d/%Y"
    suspense_account: Expenses:Uncategorized
    rules:
      - pattern: "restaurant"
        account: Expenses:Meals
""",
    )

    _write(
        project_root / "config" / "chart_of_accounts.yaml",
        """\
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Cash
    name: Cash
    type: asset
  - code: Expenses:Uncategorized
    name: Uncategorized
    type: expense
  - code: Expenses:Meals
    name: Meals
    type: expense
""",
    )

    _write(
        project_root / "inputs" / "2026-01" / "bank.csv",
        """\
Date,Description,Amount
01/02/2026,Coffee Shop,-5.20
01/03/2026,Restaurant ABC,-20.00
""",
    )

    outdir = project_root / "_out_check"
    rc = main(["check", "--project", str(project_root), "--outdir", str(outdir)])
    assert rc == 0

    assert (outdir / "checks.md").exists()
    assert (outdir / "staging.csv").exists()
    assert (outdir / "staging_issues.csv").exists()

    staging = pd.read_csv(outdir / "staging.csv")
    assert len(staging) == 2

    issues = pd.read_csv(outdir / "staging_issues.csv")
    assert "source_row_number" in issues.columns
    # Unmapped entry should surface as a warning with the original row number.
    unmapped = issues[issues["code"] == "unmapped_suspense"]
    assert len(unmapped) == 1
    assert int(unmapped.iloc[0]["source_row_number"]) == 1


def test_cli_check_fails_on_unknown_accounts(tmp_path: Path) -> None:
    project_root = tmp_path

    _write(
        project_root / "ledgerloom.yaml",
        """\
schema_id: ledgerloom.project_config.v1
project:
  name: Demo Books
  period: 2026-01
chart_of_accounts: config/chart_of_accounts.yaml
sources:
  - source_type: bank_feed.v1
    name: Checking
    file_pattern: "*.csv"
    default_account: Assets:Cash
    columns:
      date: Date
      description: Description
      amount: Amount
    date_format: "%m/%d/%Y"
    suspense_account: Expenses:Uncategorized
    rules:
      - pattern: "restaurant"
        account: Expenses:Meals
""",
    )

    # Intentionally omit Expenses:Meals from the COA.
    _write(
        project_root / "config" / "chart_of_accounts.yaml",
        """\
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Cash
    name: Cash
    type: asset
  - code: Expenses:Uncategorized
    name: Uncategorized
    type: expense
""",
    )

    _write(
        project_root / "inputs" / "2026-01" / "bank.csv",
        """\
Date,Description,Amount
01/03/2026,Restaurant ABC,-20.00
""",
    )

    outdir = project_root / "_out_check"
    rc = main(["check", "--project", str(project_root), "--outdir", str(outdir)])
    assert rc == 1

    issues = pd.read_csv(outdir / "staging_issues.csv")
    assert "unknown_account" in set(issues["code"].tolist())
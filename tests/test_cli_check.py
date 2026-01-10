from __future__ import annotations

from pathlib import Path

import shutil

import pandas as pd

from ledgerloom.cli import main
from ledgerloom.project.reclass import RECLASS_TEMPLATE_COLUMNS


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
    assert (outdir / "unmapped.csv").exists()
    assert (outdir / "reclass_template.csv").exists()

    staging = pd.read_csv(outdir / "staging.csv")
    assert len(staging) == 2

    issues = pd.read_csv(outdir / "staging_issues.csv")
    assert "source_row_number" in issues.columns
    # Unmapped entry should surface as a warning with the original row number.
    unmapped = issues[issues["code"] == "unmapped_suspense"]
    assert len(unmapped) == 1
    assert int(unmapped.iloc[0]["source_row_number"]) == 1

    unmapped_csv = pd.read_csv(outdir / "unmapped.csv")
    assert len(unmapped_csv) == 1
    assert int(unmapped_csv.iloc[0]["source_row_number"]) == 1
    assert "Coffee" in str(unmapped_csv.iloc[0]["original_description"])

    assert "suggested_pattern" in unmapped_csv.columns
    assert "suggested_rule_yaml" in unmapped_csv.columns
    assert "(?i)" in str(unmapped_csv.iloc[0]["suggested_pattern"])
    snippet = str(unmapped_csv.iloc[0]["suggested_rule_yaml"])
    assert snippet.startswith("- { pattern:")
    assert "account:" in snippet
    assert "REPLACE_ME" in snippet

    reclass_csv = pd.read_csv(outdir / "reclass_template.csv", keep_default_na=False)
    assert list(reclass_csv.columns) == RECLASS_TEMPLATE_COLUMNS
    # In this fixture, exactly one row is unmapped (Paycheck).
    assert len(reclass_csv) == 1
    assert reclass_csv.loc[0, "reclass_account"] == ""
    assert "TODO" in str(reclass_csv.loc[0, "note"])




def test_cli_check_handles_fully_mapped_inputs_and_writes_empty_issue_headers(tmp_path: Path) -> None:
    project_root = tmp_path / "p0"
    (project_root / "config").mkdir(parents=True, exist_ok=True)

    _write(
        project_root / "ledgerloom.yaml",
        """\
schema_id: ledgerloom.project_config.v1
project:
  name: Demo Books
  period: 2026-01
  currency: USD
chart_of_accounts: config/chart_of_accounts.yaml
strict_unmapped: false
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
      - pattern: "(?i)coffee"
        account: Expenses:Meals
outputs:
  root: outputs
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
01/02/2026,Coffee,-4.50
""",
    )

    outdir = project_root / "_out_check"
    rc = main(["check", "--project", str(project_root), "--outdir", str(outdir)])
    assert rc == 0

    assert (outdir / "staging_issues.csv").exists()
    assert (outdir / "unmapped.csv").exists()
    assert (outdir / "reclass_template.csv").exists()

    issues = pd.read_csv(outdir / "staging_issues.csv")
    assert list(issues.columns) == [
        "severity",
        "code",
        "message",
        "source_name",
        "source_file",
        "source_row_number",
        "column",
        "raw_value",
        "account",
    ]
    assert len(issues) == 0

    unmapped = pd.read_csv(outdir / "unmapped.csv")
    assert list(unmapped.columns) == [
        "entry_id",
        "date",
        "source_name",
        "source_file",
        "source_row_number",
        "original_description",
        "original_amount",
        "debit_account",
        "credit_account",
        "suspense_account",
        "suggested_pattern",
        "suggested_rule_yaml",
    ]
    assert len(unmapped) == 0

    reclass = pd.read_csv(outdir / "reclass_template.csv", keep_default_na=False)
    assert list(reclass.columns) == RECLASS_TEMPLATE_COLUMNS
    assert len(reclass) == 0


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
def test_cli_check_strict_unmapped_controls_exit_code(tmp_path: Path) -> None:
    # Non-strict project: unmapped rows are warnings and check passes.
    root1 = tmp_path / "p1"
    (root1 / "config").mkdir(parents=True, exist_ok=True)

    _write(
        root1 / "config" / "chart_of_accounts.yaml",
        """\
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Checking
    name: Checking
    type: asset
  - code: Expenses:Uncategorized
    name: Uncategorized
    type: expense
""",
    )

    _write(
        root1 / "ledgerloom.yaml",
        """\
schema_id: ledgerloom.project_config.v1
project:
  name: Test
  period: 2026-01
  currency: USD
chart_of_accounts: config/chart_of_accounts.yaml
strict_unmapped: false
sources:
  - source_type: bank_feed.v1
    name: Checking
    file_pattern: "*.csv"
    default_account: Assets:Checking
    columns:
      date: Date
      description: Description
      amount: Amount
    date_format: "%m/%d/%Y"
    amount_thousands_sep: ","
    amount_decimal_sep: "."
    invert_amount_sign: false
    suspense_account: Expenses:Uncategorized
    rules: []
outputs:
  root: outputs
""",
    )

    _write(
        root1 / "inputs" / "2026-01" / "bank.csv",
        """\
Date,Description,Amount
01/02/2026,Coffee,-4.50
""",
    )

    out1 = root1 / "_out_check"
    rc1 = main(["check", "--project", str(root1), "--outdir", str(out1)])
    assert rc1 == 0
    assert (out1 / "unmapped.csv").exists()

    issues1 = pd.read_csv(out1 / "staging_issues.csv")
    assert "unmapped_suspense" in set(issues1["code"].tolist())
    assert "warning" in set(issues1.loc[issues1["code"] == "unmapped_suspense", "severity"].tolist())

    # Strict project: unmapped rows become errors and check fails.
    root2 = tmp_path / "p2"
    shutil.copytree(root1 / "config", root2 / "config")
    _write(
        root2 / "ledgerloom.yaml",
        (root1 / "ledgerloom.yaml").read_text(encoding="utf-8").replace("strict_unmapped: false", "strict_unmapped: true"),
    )
    _write(
        root2 / "inputs" / "2026-01" / "bank.csv",
        """\
Date,Description,Amount
01/02/2026,Coffee,-4.50
""",
    )

    out2 = root2 / "_out_check"
    rc2 = main(["check", "--project", str(root2), "--outdir", str(out2)])
    assert rc2 == 1
    assert (out2 / "unmapped.csv").exists()

    issues2 = pd.read_csv(out2 / "staging_issues.csv")
    assert "unmapped_suspense" in set(issues2["code"].tolist())
    assert "error" in set(issues2.loc[issues2["code"] == "unmapped_suspense", "severity"].tolist())

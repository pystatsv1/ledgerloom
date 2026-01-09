from __future__ import annotations

from pathlib import Path

from ledgerloom.cli import main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_cli_suggest_mappings_reads_unmapped_and_dedupes(tmp_path: Path, capsys) -> None:
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
    rules: []
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
""",
    )

    # Two identical descriptions -> should dedupe to one rule.
    _write(
        project_root / "inputs" / "2026-01" / "bank.csv",
        """\
Date,Description,Amount
01/02/2026,Coffee,-4.50
01/03/2026,Coffee,-3.00
""",
    )

    outdir = project_root / "_out_check"
    rc = main(["check", "--project", str(project_root), "--outdir", str(outdir)])
    assert rc == 0
    assert (outdir / "unmapped.csv").exists()

    rc = main(["suggest-mappings", "--project", str(project_root), "--outdir", str(outdir)])
    assert rc == 0

    out = capsys.readouterr().out
    assert "rules:" in out
    assert "REPLACE_ME" in out
    rule_lines = [ln for ln in out.splitlines() if ln.strip().startswith("- pattern:")]
    assert len(rule_lines) == 1
    assert "coffee" in out.lower()

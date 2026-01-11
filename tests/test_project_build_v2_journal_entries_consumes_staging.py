from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerloom.project.build import run_build


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_build_v2_journal_entries_compiles_from_check_staging_postings(tmp_path: Path) -> None:
    """PR-D1: build should not re-parse source CSVs; it should compile check IR."""

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
  - code: Revenue:Sales
    name: Sales
    type: revenue
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
  - source_type: journal_entries.v1
    name: Adjustments
    file_pattern: journal.csv
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
        project_root / "inputs" / "2026-01" / "journal.csv",
        """\
entry_id,date,narration,account,debit,credit
A1,2026-01-15,Sale,Assets:Cash,100.00,
A1,2026-01-15,Sale,Revenue:Sales,,100.00
""",
    )

    res = run_build(project_root=project_root, run_id="TEST")

    postings = pd.read_csv(res.run_root / "artifacts" / "postings.csv")
    # The journal entry_id is synthesized from the check IR (staging_postings.csv).
    assert any(postings["entry_id"].astype(str).str.contains("journal:adjustments:journal.csv:A1"))

    tb = pd.read_csv(res.run_root / "artifacts" / "trial_balance.csv", dtype=str, keep_default_na=False)
    # Signed balances in normal root orientation.
    cash = tb.loc[tb["account"] == "Assets:Cash", "balance"].iloc[0]
    sales = tb.loc[tb["account"] == "Revenue:Sales", "balance"].iloc[0]
    assert cash == "100.00"
    assert sales == "100.00"

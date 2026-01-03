from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def test_ch01_script_writes_expected_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    # Run via module to match Makefile/CI behavior.
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch01_journal_vs_eventlog",
        "--outdir",
        str(tmp_path),
        "--seed",
        "123",
    ]
    subprocess.run(cmd, check=True, cwd=repo_root)

    outdir = tmp_path / "ch01"
    assert (outdir / "ledger.jsonl").exists()
    assert (outdir / "trial_balance.csv").exists()
    assert (outdir / "income_statement.csv").exists()
    assert (outdir / "balance_sheet.csv").exists()
    assert (outdir / "entry_explanations.md").exists()

    # Basic invariant check: Balance Sheet "Check" should be 0.
    # balance_sheet.csv is a 2-column CSV: index, amount
    with (outdir / "balance_sheet.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    check_rows = [r for r in rows if r and r[0] == "Check"]
    assert check_rows, "Expected a 'Check' row in balance_sheet.csv"
    check_val = float(check_rows[0][1])
    assert abs(check_val) < 1e-9

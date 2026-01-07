from __future__ import annotations

import csv
import json
import os
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
    env = dict(os.environ)
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, check=True, cwd=repo_root, env=env)

    outdir = tmp_path / "ch01"
    expected = [
        "ledger.jsonl",
        "eventlog.jsonl",
        "journal.csv",
        "ledger_view.csv",
        "trial_balance.csv",
        "income_statement.csv",
        "balance_sheet.csv",
        "entry_balancing.csv",
        "account_rollup.csv",
        "root_bar_chart.md",
        "entry_explanations.md",
        "assumptions.md",
        "checks.md",
        "tables.md",
        "lineage.mmd",
        "run_meta.json",
        "manifest.json",
        "summary.md",
    ]
    for name in expected:
        assert (outdir / name).exists(), f"Missing expected artifact: {name}"

    # eventlog.jsonl is a friendly alias for ledger.jsonl.
    assert (outdir / "eventlog.jsonl").read_text(encoding="utf-8") == (
        outdir / "ledger.jsonl"
    ).read_text(encoding="utf-8")

    # Basic invariant check: Balance Sheet "Check" should be 0.
    with (outdir / "balance_sheet.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    check = [r for r in rows if r.get("account") == "Check"]
    assert check, "Expected a 'Check' row in balance_sheet.csv"
    check_val = float(check[0]["amount"])
    assert abs(check_val) < 1e-9

    # Manifest should be JSON and should describe key artifacts.
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    names = {a["name"] for a in manifest["artifacts"]}
    assert "ledger.jsonl" in names
    assert "journal.csv" in names
    assert "run_meta.json" in names

    # Golden-file checks (byte-for-byte) to prevent cross-platform drift.
    golden_dir = Path(__file__).parent / "golden" / "ch01"
    assert golden_dir.exists(), "missing golden directory for ch01"

    golden_files = [
        "ledger.jsonl",
        "journal.csv",
        "trial_balance.csv",
        "income_statement.csv",
        "balance_sheet.csv",
        "manifest.json",
    ]

    for name in golden_files:
        got = (outdir / name).read_bytes()
        exp = (golden_dir / name).read_bytes()
        assert got == exp, f"golden mismatch for {name}"

"""Golden-file tests for LedgerLoom Chapter 04.

These tests intentionally compare bytes to catch platform-specific newline issues.
The runner forces LF (\n) for all generated CSVs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_ch04(outdir_root: Path) -> Path:
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch04_general_ledger_database",
        "--outdir",
        str(outdir_root),
        "--seed",
        "123",
    ]
    subprocess.run(cmd, check=True)
    return outdir_root / "ch04"


def test_ch04_runner_writes_expected_files(tmp_path: Path) -> None:
    outdir = _run_ch04(tmp_path)

    expected = {
        "postings.csv",
        "balances_by_account.csv",
        "balances_by_period.csv",
        "balances_by_department.csv",
        "gl_schema.json",
        "invariants.json",
        "sql_mental_model.md",
        "lineage.mmd",
        "manifest.json",
        "run_meta.json",
    }

    got = {p.name for p in outdir.iterdir() if p.is_file()}
    missing = expected - got
    assert not missing, f"missing expected artifacts: {sorted(missing)}"


def test_ch04_golden_files(tmp_path: Path) -> None:
    outdir = _run_ch04(tmp_path)

    golden_dir = Path(__file__).parent / "golden" / "ch04"
    assert golden_dir.exists()

    golden_files = [
        "postings.csv",
        "balances_by_account.csv",
        "balances_by_period.csv",
        "balances_by_department.csv",
        "gl_schema.json",
        "invariants.json",
        "manifest.json",
    ]

    for name in golden_files:
        got = (outdir / name).read_bytes()
        exp = (golden_dir / name).read_bytes()
        assert got == exp, f"golden mismatch for {name}"

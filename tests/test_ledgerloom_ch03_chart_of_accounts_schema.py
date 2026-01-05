from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_ch03_coa(tmp_path: Path) -> Path:
    out_root = tmp_path / "outputs" / "ledgerloom"
    out_root.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch03_chart_of_accounts_schema",
        "--outdir",
        str(out_root),
        "--seed",
        "123",
    ]
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    # Ensure local src/ is used when running from repo
    env["PYTHONPATH"] = "src"

    r = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
    assert "Wrote LedgerLoom Chapter 03 (COA schema) artifacts" in r.stdout

    outdir = out_root / "ch03AccountsSchema"
    assert outdir.exists()
    return outdir


def test_ch03_accounts_schema_outputs(tmp_path: Path) -> None:
    outdir = _run_ch03_coa(tmp_path)

    expected = [
        "coa_schema.json",
        "account_master.csv",
        "segment_dimensions.csv",
        "segment_values.csv",
        "income_statement_by_department.csv",
        "checks.md",
        "tables.md",
        "diagnostics.md",
        "lineage.mmd",
        "manifest.json",
        "run_meta.json",
        "summary.md",
    ]
    for name in expected:
        p = outdir / name
        assert p.exists(), f"missing artifact: {name}"

    checks = (outdir / "checks.md").read_text(encoding="utf-8")
    assert "PASS:" in checks
    assert "FAIL:" not in checks


def test_ch03_accounts_schema_golden_files(tmp_path: Path) -> None:
    outdir = _run_ch03_coa(tmp_path)

    golden_dir = Path(__file__).parent / "golden" / "ch03AccountsSchema"
    assert golden_dir.exists()

    golden_files = [
        "coa_schema.json",
        "account_master.csv",
        "segment_dimensions.csv",
        "segment_values.csv",
        "income_statement_by_department.csv",
    ]
    for name in golden_files:
        got = (outdir / name).read_bytes()
        exp = (golden_dir / name).read_bytes()
        assert got == exp, f"golden mismatch for {name}"

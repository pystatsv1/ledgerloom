from __future__ import annotations

from pathlib import Path

from ledgerloom.chapters.ch06_periods_accrual_timing import main as ch06_main


def _read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def test_ch06_outputs_match_golden(tmp_path: Path) -> None:
    outdir = tmp_path / "outputs"
    rc = ch06_main(["--outdir", str(outdir), "--seed", "123"])
    assert rc == 0

    got_dir = outdir / "ch06"
    assert got_dir.exists()

    golden_dir = Path("tests/golden/ch06")
    assert golden_dir.exists()

    files = [
        "postings.csv",
        "balances_by_period.csv",
        "income_statement_accrual_by_period.csv",
        "income_statement_cash_by_period.csv",
        "cutoff_diagnostics.csv",
        "balances_as_of.csv",
        "invariants.json",
        "manifest.json",
    ]

    for fname in files:
        got = _read_bytes(got_dir / fname)
        exp = _read_bytes(golden_dir / fname)
        assert got == exp, f"Mismatch in {fname}"

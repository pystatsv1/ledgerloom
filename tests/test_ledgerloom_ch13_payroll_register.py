from __future__ import annotations

from pathlib import Path

from ledgerloom.chapters import ch13_payroll_register


def test_ch13_payroll_register_golden(tmp_path: Path) -> None:
    outdir = tmp_path / "outputs"
    out_ch = ch13_payroll_register.run(outdir=outdir, seed=123)

    golden_dir = Path(__file__).parent / "golden" / "ch13"
    for name in sorted(p.name for p in golden_dir.iterdir() if p.is_file()):
        got = (out_ch / name).read_bytes()
        exp = (golden_dir / name).read_bytes()
        assert got == exp, f"mismatch in {name}"

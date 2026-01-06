from __future__ import annotations

from pathlib import Path

from ledgerloom.chapters import ch12_fixed_assets_depreciation


def test_ch12_fixed_assets_depreciation_golden(tmp_path: Path) -> None:
    outdir = tmp_path / "outputs"
    out_ch = ch12_fixed_assets_depreciation.run(outdir=outdir, seed=123)

    golden_dir = Path(__file__).parent / "golden" / "ch12"
    for name in sorted(p.name for p in golden_dir.iterdir() if p.is_file()):
        got = (out_ch / name).read_bytes()
        exp = (golden_dir / name).read_bytes()
        assert got == exp, f"mismatch in {name}"

from __future__ import annotations

from pathlib import Path

from ledgerloom.chapters.ch07_adjusting_entries_late_arriving_data import main


def _read(p: Path) -> bytes:
    return p.read_bytes()


def test_ch07_outputs_match_golden(tmp_path: Path) -> None:
    outroot = tmp_path / "outputs"
    rc = main(["--outdir", str(outroot), "--seed", "123"])
    assert rc == 0

    outdir = outroot / "ch07"
    assert outdir.exists()

    golden = Path("tests/golden/ch07")
    expected = sorted(p.name for p in golden.iterdir())

    got = sorted(p.name for p in outdir.iterdir())
    assert got == expected

    for name in expected:
        assert _read(outdir / name) == _read(golden / name)

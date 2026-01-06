from __future__ import annotations

from pathlib import Path

import ledgerloom.chapters.ch08_closing_controlled_transformation as ch08


def test_ch08_outputs_match_golden(tmp_path: Path) -> None:
    outroot = tmp_path / "outputs"
    ch08.main(["--outdir", str(outroot), "--seed", "123"])

    got_dir = outroot / "ch08"
    gold_dir = Path("tests/golden/ch08")

    assert gold_dir.exists(), "Golden directory missing: tests/golden/ch08"

    files = sorted(p.name for p in gold_dir.glob("*"))
    assert files, "No golden files found for Ch08"

    for name in files:
        got = got_dir / name
        gold = gold_dir / name
        assert got.exists(), f"Missing output: {name}"
        assert got.read_text(encoding="utf-8") == gold.read_text(encoding="utf-8"), f"Mismatch in {name}"

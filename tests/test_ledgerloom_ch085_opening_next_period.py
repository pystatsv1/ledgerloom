from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_ch085_outputs_match_golden(tmp_path: Path) -> None:
    outdir = tmp_path / "outputs"
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch085_opening_next_period",
        "--outdir",
        str(outdir),
        "--seed",
        "123",
    ]
    subprocess.check_call(cmd)

    got = outdir / "ch085"
    assert got.exists()

    golden = Path("tests/golden/ch085")
    assert golden.exists()

    for name in sorted(p.name for p in golden.iterdir() if p.is_file()):
        assert (got / name).read_text(encoding="utf-8") == (golden / name).read_text(encoding="utf-8")

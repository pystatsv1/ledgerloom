from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _run_ch05(tmp_path: Path) -> Path:
    outroot = tmp_path / "outputs" / "ledgerloom"
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch05_accounting_equation_invariant",
        "--outdir",
        str(outroot),
        "--seed",
        "123",
    ]
    # venv-safe runner: tests execute with current python on PATH.
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return outroot / "ch05"


def test_ch05_outputs_exist(tmp_path: Path) -> None:
    outdir = _run_ch05(tmp_path)
    assert outdir.exists()
    for name in [
        "postings.csv",
        "equation_check_by_entry.csv",
        "invariants.json",
        "manifest.json",
    ]:
        assert (outdir / name).exists()


@pytest.mark.parametrize(
    "fname",
    [
        "postings.csv",
        "equation_check_by_entry.csv",
        "invariants.json",
        "manifest.json",
    ],
)
def test_ch05_golden_files(tmp_path: Path, fname: str) -> None:
    outdir = _run_ch05(tmp_path)
    got = (outdir / fname).read_bytes()
    exp = (Path(__file__).parent / "golden" / "ch05" / fname).read_bytes()
    assert got == exp, f"{fname} did not match golden output"

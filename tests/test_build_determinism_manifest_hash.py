from __future__ import annotations

import hashlib
from pathlib import Path

from ledgerloom.project.build import run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_inputs(project_root: Path, *, period: str) -> None:
    inputs_dir = project_root / "inputs" / period
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "bank.csv").write_text(
        "Date,Description,Amount\n"
        "2026-01-02,Coffee,-4.50\n"
        "2026-01-03,Rent,-1000.00\n",
        encoding="utf-8",
        newline="\n",
    )


def test_manifest_hash_is_deterministic_across_run_ids(tmp_path: Path) -> None:
    """Same inputs/config must yield the same manifest bytes/sha, regardless of run_id."""

    project_root = tmp_path / "demo_books"
    period = "2026-01"
    create_project_skeleton(project_root, opts=InitOptions(project_name="Demo", period=period, currency="USD"))
    _write_inputs(project_root, period=period)

    r1 = run_build(project_root=project_root, run_id="run-1")
    r2 = run_build(project_root=project_root, run_id="run-2")

    m1 = r1.run_root / "trust" / "manifest.json"
    m2 = r2.run_root / "trust" / "manifest.json"

    assert m1.exists()
    assert m2.exists()

    assert _sha256_file(m1) == _sha256_file(m2)

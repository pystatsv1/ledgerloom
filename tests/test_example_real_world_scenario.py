from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from ledgerloom.project.build import run_build


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def test_example_real_world_scenario_build_is_deterministic(tmp_path: Path) -> None:
    """CI smoke: build the repo example project and assert deterministic manifest."""

    repo_root = Path(__file__).resolve().parents[1]
    example_root = repo_root / "examples" / "real_world_scenario"
    assert example_root.exists(), "Expected examples/real_world_scenario to exist in the repo"

    project_root = tmp_path / "real_world_scenario"
    # The example may have local build outputs from a developer run; exclude them so the test is robust.
    ignore = shutil.ignore_patterns("outputs", "__pycache__", ".pytest_cache")
    shutil.copytree(example_root, project_root, ignore=ignore)

    r1 = run_build(project_root=project_root, run_id="run-a")
    r2 = run_build(project_root=project_root, run_id="run-b")

    for r in (r1, r2):
        m = r.run_root / "trust" / "manifest.json"
        assert m.exists()

        # Core accounting artifacts
        assert (r.run_root / "artifacts" / "postings.csv").exists()
        assert (r.run_root / "artifacts" / "trial_balance.csv").exists()
        assert (r.run_root / "artifacts" / "income_statement.csv").exists()
        assert (r.run_root / "artifacts" / "balance_sheet.csv").exists()

        # Exception workflow artifacts
        assert (r.run_root / "artifacts" / "unmapped.csv").exists()
        assert (r.run_root / "artifacts" / "reclass_template.csv").exists()

    assert _sha256_file(r1.run_root / "trust" / "manifest.json") == _sha256_file(
        r2.run_root / "trust" / "manifest.json"
    )

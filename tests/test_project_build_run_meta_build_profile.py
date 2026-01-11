from __future__ import annotations

import json
from pathlib import Path

import yaml

from ledgerloom.project.build import run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def test_build_run_meta_includes_build_profile(tmp_path: Path) -> None:
    project_root = tmp_path / "demo_project"
    create_project_skeleton(
        project_root,  # dest
        opts=InitOptions(project_name="Demo", period="2026-01", currency="USD"),
    )

    cfg_path = project_root / "ledgerloom.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["build_profile"] = "workbook"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    res = run_build(project_root=project_root, run_id="r1", snapshot=False)

    run_meta_path = res.trust_outdir / "run_meta.json"
    run_meta = json.loads(run_meta_path.read_text(encoding="utf-8"))
    assert run_meta["build_profile"] == "workbook"

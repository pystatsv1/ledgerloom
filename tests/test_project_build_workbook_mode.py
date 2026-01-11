from __future__ import annotations

import json
import re
from pathlib import Path

from ledgerloom.project.build import run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def _enable_workbook_mode(cfg_path: Path) -> None:
    text = cfg_path.read_text(encoding="utf-8")

    if re.search(r"^build_profile:\s*", text, flags=re.MULTILINE):
        text = re.sub(r"^build_profile:.*$", "build_profile: workbook", text, flags=re.MULTILINE)
    else:
        text = text.replace(
            "strict_unmapped: false",
            "strict_unmapped: false\nbuild_profile: workbook",
        )

    cfg_path.write_text(text, encoding="utf-8", newline="\n")


def test_build_workbook_mode_emits_entries_csv_only(tmp_path: Path) -> None:
    project_root = tmp_path / "demo_project"
    create_project_skeleton(
        project_root,
        opts=InitOptions(project_name="Demo", period="2026-01", currency="USD"),
    )

    cfg_path = project_root / "ledgerloom.yaml"
    _enable_workbook_mode(cfg_path)

    res = run_build(project_root=project_root, run_id="workbook")

    artifacts_dir = res.run_root / "artifacts"
    entries_csv = artifacts_dir / "entries.csv"

    assert entries_csv.exists()
    assert not (artifacts_dir / "postings.csv").exists()
    assert not (artifacts_dir / "trial_balance.csv").exists()
    assert not (artifacts_dir / "income_statement.csv").exists()
    assert not (artifacts_dir / "balance_sheet.csv").exists()

    # Ensure trust manifest tracks entries.csv in workbook profile.
    # Note: manifest["artifacts"] is a mapping: rel_path -> {bytes, sha256}.
    manifest_path = res.run_root / "trust" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_paths = set(manifest.get("artifacts", {}).keys())
    assert "artifacts/entries.csv" in artifact_paths
    assert "artifacts/postings.csv" not in artifact_paths

    # Headers are stable even when the file is empty.
    header = entries_csv.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header[:4] == ["entry_id", "date", "narration", "entry_kind"]

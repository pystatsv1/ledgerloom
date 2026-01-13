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
    assert (artifacts_dir / "trial_balance_unadjusted.csv").exists()
    assert (artifacts_dir / "trial_balance_adjusted.csv").exists()
    assert (artifacts_dir / "closing_entries.csv").exists()
    assert (artifacts_dir / "trial_balance_post_close.csv").exists()

    assert not (artifacts_dir / "trial_balance.csv").exists()
    assert not (artifacts_dir / "income_statement.csv").exists()
    assert not (artifacts_dir / "balance_sheet.csv").exists()

    # Ensure trust manifest tracks entries.csv in workbook profile.
    # Note: manifest["artifacts"] is a mapping: rel_path -> {bytes, sha256}.
    manifest_path = res.run_root / "trust" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_paths = set(manifest.get("artifacts", {}).keys())
    assert "artifacts/entries.csv" in artifact_paths
    assert "artifacts/trial_balance_unadjusted.csv" in artifact_paths
    assert "artifacts/trial_balance_adjusted.csv" in artifact_paths
    assert "artifacts/closing_entries.csv" in artifact_paths
    assert "artifacts/trial_balance_post_close.csv" in artifact_paths
    assert "artifacts/postings.csv" not in artifact_paths


    # Post-close TB is Balance-Sheet-only (temporary accounts removed).
    tb_post_close = (artifacts_dir / "trial_balance_post_close.csv").read_text(encoding="utf-8").splitlines()
    # Header + rows
    assert tb_post_close, "trial_balance_post_close.csv should not be empty"
    # Parse roots column (account,root,balance)
    roots = {line.split(",")[1] for line in tb_post_close[1:] if line.strip() != ""}
    assert roots.issubset({"Assets", "Liabilities", "Equity"})
    # Also ensure dividends/draw accounts are not present by name.
    accounts = {line.split(",")[0] for line in tb_post_close[1:] if line.strip() != ""}
    assert not any(a.split(":")[-1].lower() in {"dividends", "dividend", "draw", "draws"} for a in accounts)
    # Headers are stable even when the file is empty.
    header = entries_csv.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header[:4] == ["entry_id", "date", "narration", "entry_kind"]

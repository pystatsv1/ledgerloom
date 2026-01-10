from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ledgerloom.project.build import run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def test_build_empty_project_writes_empty_postings_and_manifest(tmp_path: Path) -> None:
    """Building a freshly-initialized project (no CSVs yet) should not crash.

    Regression test for a pandas KeyError when sorting an empty postings table.
    """

    project_root = tmp_path / "demo_books"
    create_project_skeleton(
        project_root,
        opts=InitOptions(project_name="demo_books", period="2026-01"),
    )

    res = run_build(project_root=project_root, run_id="empty")

    postings_csv = res.run_root / "artifacts" / "postings.csv"
    manifest_path = res.run_root / "trust" / "manifest.json"

    assert postings_csv.exists()
    assert manifest_path.exists()

    df = pd.read_csv(postings_csv)
    assert "date" in df.columns
    assert df.empty

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "artifacts/postings.csv" in manifest["artifacts"]

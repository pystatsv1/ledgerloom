from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ledgerloom.project.build import BuildAbortError, run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def _write_inputs(project_root: Path, *, period: str) -> None:
    inputs_dir = project_root / "inputs" / period
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "bank.csv").write_text(
        "Date,Description,Amount\n"
        "01/03/2026,Coffee,-5.00\n"
        "01/04/2026,Rent,-1200.00\n",
        encoding="utf-8",
        newline="\n",
    )


def test_build_writes_unmapped_and_reclass_and_posts_to_suspense(tmp_path: Path) -> None:
    project_root = tmp_path / "demo_books"
    period = "2026-01"
    create_project_skeleton(project_root, opts=InitOptions(project_name="Demo", period=period, currency="USD"))
    _write_inputs(project_root, period=period)

    res = run_build(project_root=project_root, run_id="demo-nonstrict")

    unmapped = res.run_root / "artifacts" / "unmapped.csv"
    reclass = res.run_root / "artifacts" / "reclass_template.csv"
    postings = res.run_root / "artifacts" / "postings.csv"

    assert unmapped.exists()
    assert reclass.exists()
    assert postings.exists()

    unmapped_df = pd.read_csv(unmapped, keep_default_na=False)
    # Only "Rent" should be unmapped; "Coffee" hits the default template rule.
    assert len(unmapped_df) == 1
    assert "Rent" in str(unmapped_df.loc[0, "original_description"])

    postings_df = pd.read_csv(postings, keep_default_na=False)
    accounts = set(postings_df["account"].astype(str))
    assert "Expenses:Meals" in accounts  # mapped row
    assert "Expenses:Uncategorized" in accounts  # suspense posting for unmapped row


def test_build_strict_unmapped_aborts_but_keeps_run_folder(tmp_path: Path) -> None:
    project_root = tmp_path / "demo_books"
    period = "2026-01"
    create_project_skeleton(project_root, opts=InitOptions(project_name="Demo", period=period, currency="USD"))
    _write_inputs(project_root, period=period)

    # Flip strict_unmapped on.
    cfg_path = project_root / "ledgerloom.yaml"
    cfg_text = cfg_path.read_text(encoding="utf-8")
    cfg_path.write_text(cfg_text.replace("strict_unmapped: false", "strict_unmapped: true"), encoding="utf-8", newline="\n")

    with pytest.raises(BuildAbortError) as ei:
        run_build(project_root=project_root, run_id="demo-strict")

    e = ei.value
    assert e.run_root.exists()
    assert (e.run_root / "artifacts" / "unmapped.csv").exists()
    assert (e.run_root / "artifacts" / "reclass_template.csv").exists()

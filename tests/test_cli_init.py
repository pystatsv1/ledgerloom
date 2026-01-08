from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerloom.cli import main


def test_cli_init_creates_project_skeleton_and_check_runs(tmp_path: Path) -> None:
    dest = tmp_path / "my_books"

    rc = main(["init", str(dest), "--name", "Demo Books", "--period", "2026-01", "--currency", "USD"])
    assert rc == 0

    assert (dest / "ledgerloom.yaml").exists()
    assert (dest / "config" / "chart_of_accounts.yaml").exists()
    assert (dest / "config" / "mappings").is_dir()
    assert (dest / "inputs" / "2026-01").is_dir()
    assert (dest / "outputs").is_dir()

    # Ensure init templates are written with LF newlines (stable across OSes).
    assert b"\r\n" not in (dest / "ledgerloom.yaml").read_bytes()
    assert b"\r\n" not in (dest / "config" / "chart_of_accounts.yaml").read_bytes()

    # Gatekeeper should run even with no CSVs present (warnings are OK).
    rc2 = main(["check", "--project", str(dest)])
    assert rc2 == 0

    outdir = dest / "outputs" / "check" / "2026-01"
    assert (outdir / "checks.md").exists()
    assert (outdir / "staging.csv").exists()
    assert (outdir / "staging_issues.csv").exists()

    issues = pd.read_csv(outdir / "staging_issues.csv")
    # No errors in a freshly-initialized project.
    if not issues.empty:
        assert "error" not in set(issues["severity"].tolist())


def test_cli_init_refuses_non_empty_directory(tmp_path: Path) -> None:
    dest = tmp_path / "existing"
    dest.mkdir(parents=True)
    (dest / "already.txt").write_text("x", encoding="utf-8")

    rc = main(["init", str(dest), "--period", "2026-01"])
    assert rc == 1

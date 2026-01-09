from __future__ import annotations

from pathlib import Path

from ledgerloom.cli import main
from ledgerloom.project.build import run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def test_build_smoke_creates_trust_manifest(tmp_path: Path) -> None:
    """End-to-end smoke: init a tiny project and ensure build produces trust/manifest."""

    project_root = tmp_path / "demo_books"
    create_project_skeleton(
        project_root,
        opts=InitOptions(project_name="demo_books", period="2026-01"),
    )

    bank_csv = project_root / "inputs" / "2026-01" / "bank.csv"
    bank_csv.write_text(
        """Date,Description,Amount
01/02/2026,Coffee,-4.50
01/03/2026,Paycheck,2500.00
01/04/2026,Rent,-1200.00
""",
        encoding="utf-8",
        newline="\n",
    )

    res = run_build(project_root=project_root, run_id="demo")

    assert res.run_root.exists()
    assert (res.run_root / "trust" / "manifest.json").exists()


def test_build_missing_config_gives_clear_message(tmp_path: Path, monkeypatch, capsys) -> None:
    """If run from a non-project directory, the CLI should explain what to do."""

    monkeypatch.chdir(tmp_path)
    rc = main(["build", "--run-id", "demo"])
    out = capsys.readouterr()

    assert rc == 2
    assert "ledgerloom.yaml" in out.err.lower()
    assert "--project" in out.err

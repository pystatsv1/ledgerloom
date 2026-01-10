from __future__ import annotations

import json
from pathlib import Path

from ledgerloom.cli import main
from ledgerloom.project.build import run_build
from ledgerloom.project.init import InitOptions, create_project_skeleton


def test_build_smoke_creates_trust_manifest(tmp_path: Path) -> None:
    """End-to-end smoke: init a tiny project and ensure build produces postings + trust/manifest."""

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

    postings = res.run_root / "artifacts" / "postings.csv"
    trial_balance = res.run_root / "artifacts" / "trial_balance.csv"
    income_statement = res.run_root / "artifacts" / "income_statement.csv"
    balance_sheet = res.run_root / "artifacts" / "balance_sheet.csv"
    reclass_template = res.run_root / "artifacts" / "reclass_template.csv"
    manifest_path = res.run_root / "trust" / "manifest.json"
    assert postings.exists()
    assert trial_balance.exists()
    assert income_statement.exists()
    assert balance_sheet.exists()
    assert reclass_template.exists()
    assert manifest_path.exists()

    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "artifacts/postings.csv" in m["artifacts"]
    assert "bytes" in m["artifacts"]["artifacts/postings.csv"]
    assert "sha256" in m["artifacts"]["artifacts/postings.csv"]

    assert "artifacts/trial_balance.csv" in m["artifacts"]
    assert "bytes" in m["artifacts"]["artifacts/trial_balance.csv"]
    assert "sha256" in m["artifacts"]["artifacts/trial_balance.csv"]

    assert "artifacts/income_statement.csv" in m["artifacts"]
    assert "bytes" in m["artifacts"]["artifacts/income_statement.csv"]
    assert "sha256" in m["artifacts"]["artifacts/income_statement.csv"]

    assert "artifacts/balance_sheet.csv" in m["artifacts"]
    assert "bytes" in m["artifacts"]["artifacts/balance_sheet.csv"]
    assert "sha256" in m["artifacts"]["artifacts/balance_sheet.csv"]
    assert "artifacts/unmapped.csv" in m["artifacts"]
    assert "bytes" in m["artifacts"]["artifacts/unmapped.csv"]
    assert "sha256" in m["artifacts"]["artifacts/unmapped.csv"]

    assert "artifacts/reclass_template.csv" in m["artifacts"]
    assert "bytes" in m["artifacts"]["artifacts/reclass_template.csv"]
    assert "sha256" in m["artifacts"]["artifacts/reclass_template.csv"]




def test_build_missing_config_gives_clear_message(tmp_path: Path, monkeypatch, capsys) -> None:
    """If run from a non-project directory, the CLI should explain what to do."""

    monkeypatch.chdir(tmp_path)
    rc = main(["build", "--run-id", "demo"])
    out = capsys.readouterr()

    assert rc == 2
    assert "ledgerloom.yaml" in out.err.lower()
    assert "--project" in out.err

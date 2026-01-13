from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _run(cmd: list[str], *, env: dict[str, str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(cmd)}\n"
            f"--- stdout ---\n{res.stdout}\n"
            f"--- stderr ---\n{res.stderr}\n"
        )


def test_example_workbook_ch02_journal_to_trial_balance_cli_is_runnable_and_deterministic(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "examples" / "workbook" / "ch02_journal_to_trial_balance"
    assert src.exists(), "Expected examples/workbook/ch02_journal_to_trial_balance to exist in the repo"

    project_root = tmp_path / "ch02_journal_to_trial_balance"
    shutil.copytree(src, project_root)

    # Ensure subprocess sees the src-layout package even if tests are running without an installed wheel.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

    # 1) check (gatekeeper) should be runnable via the CLI
    _run([sys.executable, "-m", "ledgerloom", "check", "--project", str(project_root)], env=env)

    # 2) build twice with different run IDs; manifests should be byte-identical.
    for run_id in ("r1", "r2"):
        _run(
            [
                sys.executable,
                "-m",
                "ledgerloom",
                "build",
                "--project",
                str(project_root),
                "--run-id",
                run_id,
            ],
            env=env,
        )

        run_root = project_root / "outputs" / run_id
        assert (run_root / "artifacts" / "entries.csv").exists()
        assert (run_root / "artifacts" / "trial_balance_unadjusted.csv").exists()
        assert (run_root / "artifacts" / "trial_balance_adjusted.csv").exists()
        assert (run_root / "artifacts" / "closing_entries.csv").exists()
        assert (run_root / "artifacts" / "trial_balance_post_close.csv").exists()

        # Post-close TB should be Balance-Sheet-only
        tb_pc = pd.read_csv(run_root / "artifacts" / "trial_balance_post_close.csv", dtype=str)
        roots = set(tb_pc["root"].tolist()) if not tb_pc.empty else set()
        assert roots.issubset({"Assets", "Liabilities", "Equity"})

        # Trust manifest exists and tracks artifacts
        manifest_path = run_root / "trust" / "manifest.json"
        assert manifest_path.exists()
        manifest = manifest_path.read_text(encoding="utf-8")
        assert "artifacts/entries.csv" in manifest
        assert "artifacts/trial_balance_post_close.csv" in manifest

    assert _sha256_file(project_root / "outputs" / "r1" / "trust" / "manifest.json") == _sha256_file(
        project_root / "outputs" / "r2" / "trust" / "manifest.json"
    )

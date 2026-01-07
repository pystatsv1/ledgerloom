from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_ch03_posting_to_ledger_smoke(tmp_path: Path) -> None:
    out_root = tmp_path / "outputs"
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch03_posting_to_ledger",
        "--outdir",
        str(out_root),
        "--seed",
        "123",
    ]
    env = dict(**{k: v for k, v in dict(**__import__("os").environ).items()})
    env["PYTHONPATH"] = "src"

    p = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    assert p.returncode == 0, f"stderr:\n{p.stderr}\nstdout:\n{p.stdout}"

    ch03 = out_root / "ch03"
    assert ch03.exists()

    expected = [
        "journal.csv",
        "ledger_long.csv",
        "ledger_wide.csv",
        "account_balances.csv",
        "trial_balance.csv",
        "checks.md",
        "tables.md",
        "diagnostics.md",
        "lineage.mmd",
        "manifest.json",
        "run_meta.json",
        "summary.md",
    ]
    for name in expected:
        assert (ch03 / name).exists(), f"missing {name}"

    # checks.md should include PASS lines
    checks = (ch03 / "checks.md").read_text(encoding="utf-8")
    assert "PASS: entry_balances" in checks
    assert "PASS: trial_balance_totals" in checks

    # manifest.json should be valid JSON with artifacts list
    manifest = json.loads((ch03 / "manifest.json").read_text(encoding="utf-8"))
    assert "artifacts" in manifest and isinstance(manifest["artifacts"], list)
    paths = {a["path"] for a in manifest["artifacts"]}
    assert "trial_balance.csv" in paths

    # Determinism guard: CSV artifacts must use LF line endings (no CRLF),
    # so manifest hashes remain byte-stable across platforms.
    for name in [
        "journal.csv",
        "ledger_long.csv",
        "ledger_wide.csv",
        "account_balances.csv",
        "trial_balance.csv",
    ]:
        raw = (ch03 / name).read_bytes()
        assert b"\r\n" not in raw, f"CRLF found in {name}"
        assert raw.endswith(b"\n"), f"{name} must end with LF"
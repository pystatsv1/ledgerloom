from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


def test_ch02_runs_and_writes_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch02_debits_credits_encoding",
        "--outdir",
        str(tmp_path),
        "--seed",
        "123",
    ]
    env = dict(os.environ)
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(cmd, cwd=repo_root, env=env)

    out_dir = tmp_path / "ch02"
    assert out_dir.exists()

    expected = [
        "encoding_wide.csv",
        "encoding_long.csv",
        "encoding_signed.csv",
        "journal_from_wide.jsonl",
        "journal_from_long.jsonl",
        "journal_from_signed.jsonl",
        "diagnostics.md",
        "trial_balance.csv",
        "income_statement.csv",
        "balance_sheet.csv",
        "run_meta.json",
        "summary.md",
    ]
    for name in expected:
        assert (out_dir / name).exists()

    # The compiled journals should be byte-for-byte identical (determinism + equivalence).
    wide = (out_dir / "journal_from_wide.jsonl").read_text(encoding="utf-8")
    long = (out_dir / "journal_from_long.jsonl").read_text(encoding="utf-8")
    signed = (out_dir / "journal_from_signed.jsonl").read_text(encoding="utf-8")
    assert wide == long == signed

    # Meta should agree.
    meta = json.loads((out_dir / "run_meta.json").read_text(encoding="utf-8"))
    assert meta["entries_match_all"] is True
    assert meta["n_entries"] == 6

    # Each entry should balance (sum(debits) == sum(credits)).
    for line in wide.splitlines():
        obj = json.loads(line)
        debits = sum(Decimal(p["debit"]) for p in obj["postings"])
        credits = sum(Decimal(p["credit"]) for p in obj["postings"])
        assert debits == credits
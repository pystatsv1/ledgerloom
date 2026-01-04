from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


def test_ch02_runs_and_writes_outputs(tmp_path: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "ledgerloom.chapters.ch02_debits_credits_encoding",
        "--outdir",
        str(tmp_path),
        "--seed",
        "123",
    ]
    subprocess.check_call(cmd)

    out_dir = tmp_path / "ch02"
    assert out_dir.exists()

    expected = [
        "encoding_wide.csv",
        "encoding_long.csv",
        "journal_from_wide.jsonl",
        "journal_from_long.jsonl",
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
    assert wide == long

    # Meta should agree.
    meta = json.loads((out_dir / "run_meta.json").read_text(encoding="utf-8"))
    assert meta["entries_match"] is True
    assert meta["n_entries"] == 6

    # Each entry should balance (sum(debits) == sum(credits)).
    for line in wide.splitlines():
        obj = json.loads(line)
        debits = sum(Decimal(p["debit"]) for p in obj["postings"])
        credits = sum(Decimal(p["credit"]) for p in obj["postings"])
        assert debits == credits
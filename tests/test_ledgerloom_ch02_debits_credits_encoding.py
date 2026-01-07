from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ledgerloom.chapters.ch02_debits_credits_encoding import (
    build_demo_wide,
    long_to_entries,
    long_to_signed,
    main,
    wide_to_entries,
    wide_to_long,
)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_ch02_encodings_compile_to_same_journal_and_reports(tmp_path: Path) -> None:
    outdir = tmp_path / "outputs"
    rc = main(["--outdir", str(outdir), "--seed", "123"])
    assert rc == 0

    out_ch_dir = outdir / "ch02"

    # Core artifacts
    for name in [
        "encoding_wide.csv",
        "encoding_long.csv",
        "encoding_signed.csv",
        "journal_from_wide.jsonl",
        "journal_from_long.jsonl",
        "journal_from_signed.jsonl",
        "trial_balance.csv",
        "income_statement.csv",
        "balance_sheet.csv",
        "checks.md",
        "diagnostics.md",
        "tables.md",
        "lineage.mmd",
        "run_meta.json",
        "manifest.json",
        "summary.md",
    ]:
        assert (out_ch_dir / name).exists(), f"missing artifact: {name}"

    # Journal equivalence (hash-based)
    h_w = sha256(out_ch_dir / "journal_from_wide.jsonl")
    h_l = sha256(out_ch_dir / "journal_from_long.jsonl")
    h_s = sha256(out_ch_dir / "journal_from_signed.jsonl")
    assert h_w == h_l == h_s

    # Spot-check that the compile functions agree at the object level too.
    df_wide = build_demo_wide(seed=123)
    df_long = wide_to_long(df_wide)
    df_signed = long_to_signed(df_long)

    entries_w = wide_to_entries(df_wide)
    entries_l = long_to_entries(df_long)

    assert entries_w == entries_l
    assert entries_w == wide_to_entries(df_wide)  # determinism
    assert entries_w == long_to_entries(df_long)  # determinism

    # Signed compiles to the same entries as well (by construction).
    from ledgerloom.chapters.ch02_debits_credits_encoding import signed_to_entries

    entries_s = signed_to_entries(df_signed)
    assert entries_w == entries_s

    # Manifest is parseable and includes hashes
    manifest = json.loads((out_ch_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "ledgerloom.manifest.v1"
    names = {a["name"] for a in manifest["artifacts"]}
    assert "journal_from_wide.jsonl" in names
    assert "checks.md" in names
    for a in manifest["artifacts"]:
        assert "sha256" in a and isinstance(a["sha256"], str) and len(a["sha256"]) == 64


def test_ch02_golden_files(tmp_path: Path) -> None:
    """Golden-file tests to catch byte-level drift across platforms."""

    outdir = tmp_path / "outputs"
    rc = main(["--outdir", str(outdir), "--seed", "123"])
    assert rc == 0

    out_ch_dir = outdir / "ch02"
    golden_dir = Path(__file__).parent / "golden" / "ch02"
    assert golden_dir.exists(), "missing golden directory for ch02"

    golden_files = [
        "encoding_wide.csv",
        "encoding_long.csv",
        "encoding_signed.csv",
        "journal_from_wide.jsonl",
        "trial_balance.csv",
        "income_statement.csv",
        "balance_sheet.csv",
        "manifest.json",
    ]

    for name in golden_files:
        got = (out_ch_dir / name).read_bytes()
        exp = (golden_dir / name).read_bytes()
        assert got == exp, f"golden mismatch for {name}"

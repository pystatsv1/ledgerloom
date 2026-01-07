from __future__ import annotations

from pathlib import Path

from ledgerloom.chapters import ch10_ap_lifecycle as ch10


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_same_files(dir_a: Path, dir_b: Path, files: list[str]) -> None:
    for name in files:
        a = _read_text(dir_a / name)
        b = _read_text(dir_b / name)
        assert a == b, f"Mismatch in {name}"


def test_ch10_golden_outputs(tmp_path: Path) -> None:
    outdir = tmp_path / "outputs"
    out_ch = ch10.run(outdir, seed=123)

    golden = Path(__file__).parent / "golden" / "ch10"
    assert golden.exists(), "Missing tests/golden/ch10; regenerate golden fixtures"

    expected_files = [
        "postings_post_close.csv",
        "trial_balance_post_close.csv",
        "postings_opening.csv",
        "trial_balance_opening.csv",
        "reconciliation_post_close_vs_opening.csv",
        "vendor_bills_register.csv",
        "vendor_credits_register.csv",
        "cash_disbursements_register.csv",
        "postings_ap.csv",
        "ap_open_items.csv",
        "ap_control_reconciliation.csv",
        "trial_balance_end_period.csv",
        "income_statement_current_period.csv",
        "balance_sheet_current_period.csv",
        "invariants.json",
        "ap_checklist.json",
        "run_meta.json",
        "manifest.json",
    ]

    _assert_same_files(out_ch, golden, expected_files)

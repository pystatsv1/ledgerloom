"""Chapter 05 — Accounting equation as an invariant.

Goal
- Show that the ledger is not just "balanced per entry" (double-entry),
  but also balanced in aggregate: assets = liabilities + equity (+ net income).

We model this using an *expanded* equation (because we keep Revenue/Expenses open):
    Assets = Liabilities + Equity + Revenue - Expenses

Equivalently (debit-positive / credit-negative raw balances):
    Assets + Liabilities + Equity + Revenue + Expenses == 0

This chapter materializes:
- postings.csv (fact table)
- equation_check_by_entry.csv (running balances + equation diff)
- invariants.json (engine invariants + equation failures)
- manifest.json (sha256 + size for artifacts)
"""

from __future__ import annotations


import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from ledgerloom.core import Entry
from ledgerloom.engine import LedgerEngine, LedgerEngineConfig
from ledgerloom.artifacts import manifest_items, write_csv_df, write_json
from ledgerloom.trust.pipeline import emit_trust_artifacts


 # Chapter-owned deterministic I/O helpers live in ledgerloom.artifacts.


def _sample_entries(seed: int) -> List[Entry]:
    """Small, deterministic set of entries that touches all roots."""
    # seed is included in meta for lineage/debug (even if not used for randomness here)
    def e(entry_id: str, dt: date, narration: str, lines: List[Tuple[str, str, str]]) -> Entry:
        ps = []
        for acct, dr, cr in lines:
            ps.append(
                {
                    "account": acct,
                    "debit": Decimal(dr),
                    "credit": Decimal(cr),
                }
            )
        postings = []
        from ledgerloom.core import Posting  # local import to keep top-level clean

        for p in ps:
            postings.append(Posting(account=p["account"], debit=p["debit"], credit=p["credit"]))

        return Entry(
            dt=dt,
            narration=narration,
            postings=postings,
            meta={"entry_id": entry_id, "seed": str(seed)},
        )

    return [
        e(
            "E0001",
            date(2025, 1, 2),
            "Owner invests cash to start the business",
            [
                ("Assets:Cash", "1000.00", "0"),
                ("Equity:OwnerCapital", "0", "1000.00"),
            ],
        ),
        e(
            "E0002",
            date(2025, 1, 5),
            "Buy supplies on account",
            [
                ("Assets:Supplies", "200.00", "0"),
                ("Liabilities:AccountsPayable", "0", "200.00"),
            ],
        ),
        e(
            "E0003",
            date(2025, 1, 9),
            "Provide services for cash",
            [
                ("Assets:Cash", "500.00", "0"),
                ("Revenue:ServiceRevenue", "0", "500.00"),
            ],
        ),
        e(
            "E0004",
            date(2025, 1, 15),
            "Pay monthly rent",
            [
                ("Expenses:Rent", "300.00", "0"),
                ("Assets:Cash", "0", "300.00"),
            ],
        ),
        e(
            "E0005",
            date(2025, 1, 20),
            "Pay a portion of accounts payable",
            [
                ("Liabilities:AccountsPayable", "150.00", "0"),
                ("Assets:Cash", "0", "150.00"),
            ],
        ),
    ]


def _resolve_outdir(outdir_root: str) -> Path:
    root = Path(outdir_root)
    return root / "ch05"


def _equation_check_by_entry(postings: pd.DataFrame) -> pd.DataFrame:
    """Compute running balances and the expanded equation check, per entry."""
    tmp = postings.copy()

    # raw_delta is debit-credit (debit positive, credit negative) expressed as a string.
    tmp["raw_delta_cents"] = tmp["raw_delta"].map(lambda s: int(Decimal(s) * 100))

    # Per-entry per-root deltas
    g = (
        tmp.groupby(["entry_id", "date", "root"], sort=False)["raw_delta_cents"]
        .sum()
        .reset_index()
        .sort_values(["date", "entry_id", "root"], kind="mergesort")
        .reset_index(drop=True)
    )

    # Establish stable entry order (by first appearance)
    entry_order = (
        tmp[["entry_id", "date"]]
        .drop_duplicates()
        .sort_values(["date", "entry_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    entry_order["entry_no"] = range(1, len(entry_order) + 1)

    # Pivot roots to columns
    piv = (
        g.pivot_table(index=["entry_id", "date"], columns="root", values="raw_delta_cents", aggfunc="sum", fill_value=0)
        .reset_index()
    )

    # Ensure consistent column set even if a root is absent in the sample.
    for root in ["Assets", "Liabilities", "Equity", "Revenue", "Expenses"]:
        if root not in piv.columns:
            piv[root] = 0

    piv = piv.merge(entry_order, on=["entry_id", "date"], how="left").sort_values(["entry_no"], kind="mergesort")
    piv = piv.reset_index(drop=True)

    # Running balances (cumulative)
    for root in ["Assets", "Liabilities", "Equity", "Revenue", "Expenses"]:
        piv[f"{root}_bal_cents"] = piv[root].cumsum()

    # Convert to human-friendly positive values for the expanded equation
    # Assets/Expenses are normally debit (raw balances usually >= 0)
    # Liabilities/Equity/Revenue are normally credit (raw balances usually <= 0)
    def money(cents: int) -> str:
        return f"{Decimal(cents) / Decimal(100):.2f}"

    assets = piv["Assets_bal_cents"]
    liabilities = -piv["Liabilities_bal_cents"]
    equity = -piv["Equity_bal_cents"]
    revenue = -piv["Revenue_bal_cents"]
    expenses = piv["Expenses_bal_cents"]

    rhs = liabilities + equity + revenue - expenses
    diff = assets - rhs

    out = pd.DataFrame(
        {
            "entry_no": piv["entry_no"],
            "date": piv["date"],
            "entry_id": piv["entry_id"],
            "assets": assets.map(money),
            "liabilities": liabilities.map(money),
            "equity": equity.map(money),
            "revenue": revenue.map(money),
            "expenses": expenses.map(money),
            "rhs_liab_plus_equity_plus_rev_minus_exp": rhs.map(money),
            "diff_assets_minus_rhs": diff.map(money),
            "equation_ok": diff.eq(0).map(lambda b: "true" if b else "false"),
        }
    )
    return out


def run(outdir_root: str, seed: int) -> Path:
    outdir = _resolve_outdir(outdir_root)
    outdir.mkdir(parents=True, exist_ok=True)

    entries = _sample_entries(seed)
    cfg = LedgerEngineConfig()
    engine = LedgerEngine(cfg)

    postings = engine.postings_fact_table(entries)

    equation_check = _equation_check_by_entry(postings)
    eq_failures = equation_check.loc[equation_check["equation_ok"] != "true", "entry_id"].tolist()

    inv = engine.invariants(entries, postings)
    inv2 = dict(inv)
    inv2["accounting_equation_entry_failures"] = eq_failures
    inv2["accounting_equation_ok"] = len(eq_failures) == 0
    inv2["notes"] = list(inv2.get("notes", [])) + [
        "Expanded equation checked: Assets = Liabilities + Equity + Revenue - Expenses (open temporary accounts).",
    ]

    artifacts: List[Path] = []

    postings_path = outdir / "postings.csv"
    write_csv_df(postings_path, postings)
    artifacts.append(postings_path)

    eq_path = outdir / "equation_check_by_entry.csv"
    write_csv_df(eq_path, equation_check)
    artifacts.append(eq_path)

    inv_path = outdir / "invariants.json"
    write_json(inv_path, inv2)
    artifacts.append(inv_path)

    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        'chapter': 'ch05',
        'module': 'ledgerloom.chapters.ch05_accounting_equation_invariant',
        'seed': seed,
        'entries': len(entries),
        'postings': int(len(postings)),
    }

    def _manifest_payload(d: Path) -> dict[str, object]:
        files = list(artifacts) + [d / 'run_meta.json']
        return {'artifacts': manifest_items(d, files, name_key='file')}

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    return outdir


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outdir", default="outputs/ledgerloom", help="Output root directory.")
    p.add_argument("--seed", type=int, default=123, help="Deterministic seed for the runner.")
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = _parse_args(argv)
    outdir = run(args.outdir, args.seed)
    print(f"Wrote LedgerLoom Chapter 05 artifacts -> {outdir}")


if __name__ == "__main__":
    main()

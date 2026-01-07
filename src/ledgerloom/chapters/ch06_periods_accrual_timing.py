"""LedgerLoom Chapter 06 — Periods, accrual, and timing.

This chapter introduces **accounting periods** and the idea that *timing* matters.

Two measurement lenses
----------------------
1) **Accrual basis** (the default in financial reporting):
   - Revenue is recognized when it is earned (e.g., an invoice is issued).
   - Expenses are recognized when they are incurred (even if paid later).

2) **Cash basis** (a useful mental model, and common for very small businesses):
   - Revenue is recognized when cash is received.
   - Expenses are recognized when cash is paid.

From a data perspective, both are **derived views** over the same immutable event log.
The difference is *when* you treat an event as impacting the income statement.

Run:
    python -m ledgerloom.chapters.ch06_periods_accrual_timing --outdir outputs/ledgerloom --seed 123

Artifacts land under:
    outputs/ledgerloom/ch06
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine
from ledgerloom.artifacts import manifest_items, write_csv_df, write_json
from ledgerloom.trust.pipeline import emit_trust_artifacts


 # Chapter-owned I/O helpers are centralized in ledgerloom.artifacts.


def _str_to_cents(s: str) -> int:
    return int(Decimal(str(s)) * 100)


def _cents_to_str(c: int) -> str:
    return f"{Decimal(c) / Decimal(100):.2f}"


# -------------------------
# Sample data
# -------------------------


def _sample_entries(seed: int) -> list[Entry]:
    """A tiny journal spanning two periods (Jan/Feb) with timing differences.

    The dataset is intentionally stable: determinism and golden-file robustness
    matter more than randomness here.

    Scenario highlights:
    - Invoice in Jan, cash collected in Feb (AR timing)
    - Utilities incurred in Jan, paid in Feb (AP timing)
    - Rent prepaid in Jan for Feb (prepaid timing)
    - A cash sale + cash expense (where cash and accrual match)
    """

    def e(entry_id: str, dt: date, narration: str, lines: list[tuple[str, str, str]]) -> Entry:
        postings: list[Posting] = []
        for acct, dr, cr in lines:
            postings.append(Posting(account=acct, debit=Decimal(dr), credit=Decimal(cr)))
        return Entry(
            dt=dt,
            narration=narration,
            postings=postings,
            meta={"entry_id": entry_id, "seed": str(seed)},
        )

    return [
        e(
            "E0001",
            date(2026, 1, 1),
            "Owner investment to start operations",
            [
                ("Assets:Cash", "1000.00", "0"),
                ("Equity:OwnerCapital", "0", "1000.00"),
            ],
        ),
        e(
            "E0002",
            date(2026, 1, 15),
            "Pay February rent in advance (prepaid rent)",
            [
                ("Assets:PrepaidRent", "200.00", "0"),
                ("Assets:Cash", "0", "200.00"),
            ],
        ),
        e(
            "E0003",
            date(2026, 1, 20),
            "Cash sale",
            [
                ("Assets:Cash", "120.00", "0"),
                ("Revenue:Sales", "0", "120.00"),
            ],
        ),
        e(
            "E0004",
            date(2026, 1, 21),
            "Buy office supplies for cash",
            [
                ("Expenses:Supplies", "30.00", "0"),
                ("Assets:Cash", "0", "30.00"),
            ],
        ),
        e(
            "E0005",
            date(2026, 1, 28),
            "Invoice customer (net 30)",
            [
                ("Assets:AccountsReceivable", "500.00", "0"),
                ("Revenue:Sales", "0", "500.00"),
            ],
        ),
        e(
            "E0006",
            date(2026, 1, 31),
            "Utilities incurred (bill arrives later)",
            [
                ("Expenses:Utilities", "60.00", "0"),
                ("Liabilities:AccountsPayable", "0", "60.00"),
            ],
        ),
        e(
            "E0007",
            date(2026, 2, 1),
            "Recognize February rent from prepaid balance",
            [
                ("Expenses:Rent", "200.00", "0"),
                ("Assets:PrepaidRent", "0", "200.00"),
            ],
        ),
        e(
            "E0008",
            date(2026, 2, 10),
            "Customer pays January invoice",
            [
                ("Assets:Cash", "500.00", "0"),
                ("Assets:AccountsReceivable", "0", "500.00"),
            ],
        ),
        e(
            "E0009",
            date(2026, 2, 15),
            "Pay utilities bill",
            [
                ("Liabilities:AccountsPayable", "60.00", "0"),
                ("Assets:Cash", "0", "60.00"),
            ],
        ),
    ]


def _resolve_outdir(outdir_root: str) -> Path:
    return Path(outdir_root) / "ch06"


# -------------------------
# Views
# -------------------------


def _accrual_income_statement_by_period(postings: pd.DataFrame) -> pd.DataFrame:
    """Accrual basis profit per period (Revenue - Expenses), derived from postings."""
    tmp = postings.copy()
    tmp["period"] = tmp["date"].str.slice(0, 7)  # YYYY-MM
    tmp["signed_cents"] = tmp["signed_delta"].map(_str_to_cents)

    g = tmp.groupby(["period", "root"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )

    # revenue and expenses are stored as positive signed balances (normal-balance convention)
    rev = g.loc[g["root"] == "Revenue", ["period", "signed_cents"]].rename(columns={"signed_cents": "revenue_cents"})
    exp = g.loc[g["root"] == "Expenses", ["period", "signed_cents"]].rename(columns={"signed_cents": "expense_cents"})

    out = pd.merge(rev, exp, on="period", how="outer").fillna(0).sort_values("period", kind="mergesort")
    out["revenue"] = out["revenue_cents"].map(lambda c: _cents_to_str(int(c)))
    out["expenses"] = out["expense_cents"].map(lambda c: _cents_to_str(int(c)))
    out["net_income"] = (out["revenue_cents"] - out["expense_cents"]).map(lambda c: _cents_to_str(int(c)))
    return out[["period", "revenue", "expenses", "net_income"]].reset_index(drop=True)


def _cash_effects_by_entry(postings: pd.DataFrame) -> pd.DataFrame:
    """Derive cash-basis income effects (revenue/expense) per entry.

    We classify *cash movements* into:
    - cash revenue: cash increases tied to either Revenue postings (cash sale) or AR collection
    - cash expense: cash decreases tied to either Expenses postings (cash purchase) or AP/prepaid settlement
    """
    tmp = postings.copy()
    tmp["period"] = tmp["date"].str.slice(0, 7)
    tmp["raw_delta_cents"] = tmp["raw_delta"].map(_str_to_cents)
    tmp["signed_cents"] = tmp["signed_delta"].map(_str_to_cents)

    rows: list[dict[str, Any]] = []
    for (entry_id, dt, period), g in tmp.groupby(["entry_id", "date", "period"], sort=False):
        cash = int(g.loc[g["account"] == "Assets:Cash", "raw_delta_cents"].sum())

        has_rev = bool((g["root"] == "Revenue").any())
        has_exp = bool((g["root"] == "Expenses").any())

        ar = int(g.loc[g["account"] == "Assets:AccountsReceivable", "raw_delta_cents"].sum())
        ap = int(g.loc[g["account"] == "Liabilities:AccountsPayable", "raw_delta_cents"].sum())
        prepaid = int(g.loc[g["account"] == "Assets:PrepaidRent", "raw_delta_cents"].sum())

        # accrual impacts (per entry)
        accrual_rev = int(g.loc[g["root"] == "Revenue", "signed_cents"].sum())
        accrual_exp = int(g.loc[g["root"] == "Expenses", "signed_cents"].sum())

        cash_rev = 0
        cash_exp = 0

        if cash > 0 and (has_rev or ar < 0):
            cash_rev = cash

        if cash < 0 and (has_exp or ap > 0 or prepaid > 0):
            cash_exp = -cash

        event = "other"
        if cash > 0 and (g["root"] == "Equity").any() and not has_rev and ar == 0:
            event = "owner_investment"
        elif has_rev and ar > 0 and cash == 0:
            event = "invoice (accrual revenue)"
        elif cash > 0 and ar < 0 and not has_rev:
            event = "collect receivable (cash revenue)"
        elif prepaid > 0 and cash < 0:
            event = "prepay expense (cash expense)"
        elif has_exp and ap < 0 and cash == 0:
            event = "accrue expense (accrual expense)"
        elif ap > 0 and cash < 0 and not has_exp:
            event = "pay payable (cash expense)"
        elif has_rev and cash > 0:
            event = "cash sale"
        elif has_exp and cash < 0:
            event = "cash expense"

        rows.append(
            {
                "date": dt,
                "period": period,
                "entry_id": entry_id,
                "event": event,
                "cash_change": _cents_to_str(cash),
                "cash_revenue": _cents_to_str(cash_rev),
                "cash_expenses": _cents_to_str(cash_exp),
                "cash_net_income_delta": _cents_to_str(cash_rev - cash_exp),
                "accrual_revenue": _cents_to_str(accrual_rev),
                "accrual_expenses": _cents_to_str(accrual_exp),
                "accrual_net_income_delta": _cents_to_str(accrual_rev - accrual_exp),
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values(["date", "entry_id"], kind="mergesort").reset_index(drop=True)
    return out


def _cash_income_statement_by_period(cash_by_entry: pd.DataFrame) -> pd.DataFrame:
    tmp = cash_by_entry.copy()
    tmp["cash_rev_cents"] = tmp["cash_revenue"].map(_str_to_cents)
    tmp["cash_exp_cents"] = tmp["cash_expenses"].map(_str_to_cents)

    g = tmp.groupby("period", sort=True, as_index=False).agg(
        cash_rev_cents=("cash_rev_cents", "sum"),
        cash_exp_cents=("cash_exp_cents", "sum"),
    )
    g["revenue"] = g["cash_rev_cents"].map(lambda c: _cents_to_str(int(c)))
    g["expenses"] = g["cash_exp_cents"].map(lambda c: _cents_to_str(int(c)))
    g["net_income"] = (g["cash_rev_cents"] - g["cash_exp_cents"]).map(lambda c: _cents_to_str(int(c)))
    return g[["period", "revenue", "expenses", "net_income"]].reset_index(drop=True)


def _balances_as_of(engine: LedgerEngine, postings: pd.DataFrame, as_of_dates: list[date]) -> pd.DataFrame:
    """Small "as-of" snapshot table for period boundaries."""
    focus_accounts = [
        "Assets:Cash",
        "Assets:AccountsReceivable",
        "Assets:PrepaidRent",
        "Liabilities:AccountsPayable",
        "Equity:OwnerCapital",
    ]

    rows: list[dict[str, str]] = []
    for d in as_of_dates:
        bal = engine.balances_by_account_as_of(postings, as_of=d)
        for acct in focus_accounts:
            got = bal.loc[bal["account"] == acct, "balance"]
            balance = got.iloc[0] if len(got) else "0.00"
            rows.append({"as_of": d.isoformat(), "account": acct, "balance": balance})

    out = pd.DataFrame(rows)
    out = out.sort_values(["as_of", "account"], kind="mergesort").reset_index(drop=True)
    return out


# -------------------------
# Main runner
# -------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LedgerLoom Chapter 06: periods, accrual, and timing")
    p.add_argument("--outdir", default="outputs/ledgerloom", help="Output root directory")
    p.add_argument("--seed", type=int, default=123, help="Deterministic seed for artifacts")
    args = p.parse_args(argv)

    outdir = _resolve_outdir(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    entries = _sample_entries(args.seed)
    for e in entries:
        e.validate_balanced()

    engine = LedgerEngine()
    postings = engine.postings_fact_table(entries)

    # Derived views for the story
    balances_period = engine.balances_by_period(postings)
    accrual_is = _accrual_income_statement_by_period(postings)
    cash_by_entry = _cash_effects_by_entry(postings)
    cash_is = _cash_income_statement_by_period(cash_by_entry)
    balances_asof = _balances_as_of(engine, postings, [date(2026, 1, 31), date(2026, 2, 28)])

    inv = engine.invariants(entries, postings)

    # A small "chapter invariant": all cash changes should be explained in this dataset.
    unexplained = cash_by_entry.loc[
        (cash_by_entry["cash_change"] != "0.00")
        & (cash_by_entry["event"].isin(["other"])),
        ["date", "entry_id", "cash_change", "event"],
    ]
    inv2 = dict(inv)
    inv2["chapter"] = "ch06"
    inv2["unexplained_cash_moves"] = unexplained.to_dict(orient="records")

    # Write artifacts (stable order)
    artifacts: list[Path] = []

    def w_csv(name: str, df: pd.DataFrame) -> None:
        path = outdir / name
        write_csv_df(path, df)
        artifacts.append(path)

    def w_json(name: str, obj: Any) -> None:
        path = outdir / name
        write_json(path, obj)
        artifacts.append(path)

    w_csv("postings.csv", postings)
    w_csv("balances_by_period.csv", balances_period)
    w_csv("income_statement_accrual_by_period.csv", accrual_is)
    w_csv("income_statement_cash_by_period.csv", cash_is)
    w_csv("cutoff_diagnostics.csv", cash_by_entry)
    w_csv("balances_as_of.csv", balances_asof)
    w_json("invariants.json", inv2)
    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        "chapter": "ch06",
        "module": "ledgerloom.chapters.ch06_periods_accrual_timing",
        "seed": args.seed,
        "entries": len(entries),
    }

    def _manifest_payload(d: Path) -> dict[str, object]:
        files = list(artifacts) + [d / "run_meta.json"]
        return {
            "artifacts": manifest_items(d, files, name_key="file"),
            "meta": {
                "chapter": "ch06",
                "seed": args.seed,
            },
        }

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    print(f"Wrote LedgerLoom Chapter 06 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

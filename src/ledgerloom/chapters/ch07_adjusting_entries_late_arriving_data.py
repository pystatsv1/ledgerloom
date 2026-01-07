"""LedgerLoom Chapter 07 — Adjusting entries as late-arriving data.

In the real world, "closing the books" is rarely a single moment. It is a workflow.

You start with an **unadjusted** close (what you know at the deadline),
then you incorporate evidence that arrives *after* period end:

- a utility bill received a few days later
- an inventory/supplies count performed after month-end
- a customer prepayment that should be deferred
- a prepaid expense that should be reclassified

In accounting terms, these are **adjusting entries**.
In data-engineering terms, they are **late-arriving events** that must be:

- separate and append-only (never overwrite history)
- attributable (who/why/when/source)
- reproducible (deterministic artifacts + tests)

Run:
    python -m ledgerloom.chapters.ch07_adjusting_entries_late_arriving_data --outdir outputs/ledgerloom --seed 123
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


...


# -------------------------
# Money helpers (deterministic)
# -------------------------


def _str_to_cents(s: str) -> int:
    """Parse a canonical money string like '-12.34' into integer cents."""
    s = str(s)
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    if "." in s:
        a, b = s.split(".", 1)
        b = (b + "00")[:2]
    else:
        a, b = s, "00"
    cents = int(a) * 100 + int(b)
    return -cents if neg else cents


def _cents_to_str(cents: int) -> str:
    neg = cents < 0
    cents = abs(int(cents))
    whole = cents // 100
    frac = cents % 100
    s = f"{whole}.{frac:02d}"
    return f"-{s}" if neg and s != "0.00" else s


def _period_from_iso_date(d: str) -> str:
    return str(d)[:7]  # YYYY-MM


# -------------------------
# Dataset
# -------------------------


def _make_entry(
    entry_id: str,
    dt: date,
    narration: str,
    lines: list[tuple[str, str, str]],
    meta: dict[str, str] | None = None,
) -> Entry:
    postings: list[Posting] = []
    for acct, dr, cr in lines:
        postings.append(Posting(account=acct, debit=Decimal(dr), credit=Decimal(cr)))
    m = {"entry_id": entry_id}
    if meta:
        m.update(meta)
    e = Entry(dt=dt, narration=narration, postings=postings, meta=m)
    e.validate_balanced()
    return e


def _base_entries() -> list[Entry]:
    """Unadjusted Jan close — recorded events as of the deadline."""
    return [
        _make_entry(
            "E0701",
            date(2026, 1, 2),
            "Owner contribution (cash)",
            [
                ("Assets:Cash", "5000.00", "0.00"),
                ("Equity:OwnerCapital", "0.00", "5000.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0702",
            date(2026, 1, 5),
            "Buy office supplies (recorded as asset)",
            [
                ("Assets:Supplies", "300.00", "0.00"),
                ("Assets:Cash", "0.00", "300.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0703",
            date(2026, 1, 10),
            "Invoice customer for services (AR)",
            [
                ("Assets:AccountsReceivable", "1200.00", "0.00"),
                ("Revenue:Sales", "0.00", "1200.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0704",
            date(2026, 1, 12),
            "Customer prepayment for February services (recorded as revenue)",
            [
                ("Assets:Cash", "400.00", "0.00"),
                ("Revenue:Sales", "0.00", "400.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0705",
            date(2026, 1, 20),
            "Pay February rent in advance (recorded as expense)",
            [
                ("Expenses:Rent", "1000.00", "0.00"),
                ("Assets:Cash", "0.00", "1000.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0706",
            date(2026, 1, 25),
            "Cash sale (earned and received)",
            [
                ("Assets:Cash", "200.00", "0.00"),
                ("Revenue:Sales", "0.00", "200.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
    ]


def _adjusting_entries() -> list[Entry]:
    """Adjustments dated 2026-01-31, but posted after month-end.

    These are the *late-arriving* events that make the close correct.
    """
    eff = date(2026, 1, 31)
    return [
        _make_entry(
            "A0701",
            eff,
            "Defer unearned revenue (move Jan prepayment to liability)",
            [
                ("Revenue:Sales", "400.00", "0.00"),
                ("Liabilities:UnearnedRevenue", "0.00", "400.00"),
            ],
            {
                "department": "HQ",
                "entry_kind": "adjustment",
                "affects_period": "2026-01",
                "posted_at": "2026-02-03",
                "prepared_by": "Controller",
                "source": "Service contract",
                "reason": "Cash received in Jan relates to Feb service delivery.",
            },
        ),
        _make_entry(
            "A0702",
            eff,
            "Reclass prepaid rent (Jan payment benefits Feb)",
            [
                ("Assets:PrepaidRent", "1000.00", "0.00"),
                ("Expenses:Rent", "0.00", "1000.00"),
            ],
            {
                "department": "HQ",
                "entry_kind": "adjustment",
                "affects_period": "2026-01",
                "posted_at": "2026-02-03",
                "prepared_by": "Controller",
                "source": "Lease agreement",
                "reason": "Rent paid in Jan is for Feb; expense should match period of benefit.",
            },
        ),
        _make_entry(
            "A0703",
            eff,
            "Accrue utilities expense (bill arrived after period end)",
            [
                ("Expenses:Utilities", "150.00", "0.00"),
                ("Liabilities:AccountsPayable", "0.00", "150.00"),
            ],
            {
                "department": "HQ",
                "entry_kind": "adjustment",
                "affects_period": "2026-01",
                "posted_at": "2026-02-04",
                "prepared_by": "Controller",
                "source": "Utility bill",
                "reason": "Utilities were consumed in Jan; invoice received in Feb.",
            },
        ),
        _make_entry(
            "A0704",
            eff,
            "Recognize supplies used (month-end count)",
            [
                ("Expenses:Supplies", "120.00", "0.00"),
                ("Assets:Supplies", "0.00", "120.00"),
            ],
            {
                "department": "HQ",
                "entry_kind": "adjustment",
                "affects_period": "2026-01",
                "posted_at": "2026-02-05",
                "prepared_by": "Controller",
                "source": "Supplies count",
                "reason": "Supplies consumed should be expensed in the period they are used.",
            },
        ),
    ]


# -------------------------
# Views (derived artifacts)
# -------------------------


def _trial_balance(postings: pd.DataFrame) -> pd.DataFrame:
    cents = postings.assign(_c=postings["signed_delta"].map(_str_to_cents)).groupby("account", as_index=False)["_c"].sum()
    cents["root"] = cents["account"].map(lambda a: str(a).split(":", 1)[0])
    cents["balance"] = cents["_c"].map(_cents_to_str)
    out = cents[["account", "root", "balance"]].sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def _income_statement(tb: pd.DataFrame) -> pd.DataFrame:
    # signed balances are already in "normal" orientation: revenue positive, expenses positive
    def s(root: str) -> int:
        return int(tb.loc[tb["root"] == root, "balance"].map(_str_to_cents).sum())

    rev = s("Revenue")
    exp = s("Expenses")
    ni = rev - exp
    return pd.DataFrame(
        [
            {"metric": "Revenue", "amount": _cents_to_str(rev)},
            {"metric": "Expenses", "amount": _cents_to_str(exp)},
            {"metric": "NetIncome", "amount": _cents_to_str(ni)},
        ]
    )


def _balance_sheet_summary(tb: pd.DataFrame) -> pd.DataFrame:
    def s(root: str) -> int:
        return int(tb.loc[tb["root"] == root, "balance"].map(_str_to_cents).sum())

    assets = s("Assets")
    liabilities = s("Liabilities")
    equity = s("Equity")
    # include net income so the equation holds even though Revenue/Expenses remain open
    inc = _income_statement(tb)
    net_income = _str_to_cents(str(inc.loc[inc["metric"] == "NetIncome", "amount"].iloc[0]))
    lhs = assets
    rhs = liabilities + equity + net_income
    diff = lhs - rhs

    return pd.DataFrame(
        [
            {"metric": "Assets", "amount": _cents_to_str(assets)},
            {"metric": "Liabilities", "amount": _cents_to_str(liabilities)},
            {"metric": "Equity", "amount": _cents_to_str(equity)},
            {"metric": "NetIncome", "amount": _cents_to_str(net_income)},
            {"metric": "EquationLHS_Assets", "amount": _cents_to_str(lhs)},
            {"metric": "EquationRHS_L+E+NI", "amount": _cents_to_str(rhs)},
            {"metric": "Difference", "amount": _cents_to_str(diff)},
        ]
    )


def _entry_register(entries: list[Entry]) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for e in entries:
        meta = e.meta or {}
        entry_id = str(meta.get("entry_id", ""))
        dt_iso = e.dt.isoformat()
        period = _period_from_iso_date(dt_iso)
        kind = str(meta.get("entry_kind", ""))
        posted_at = str(meta.get("posted_at", ""))
        affects_period = str(meta.get("affects_period", period))
        rows.append(
            {
                "entry_id": entry_id,
                "date": dt_iso,
                "period": period,
                "kind": kind,
                "posted_at": posted_at,
                "affects_period": affects_period,
                "department": str(meta.get("department", "")),
                "narration": e.narration,
                "prepared_by": str(meta.get("prepared_by", "")),
                "source": str(meta.get("source", "")),
                "reason": str(meta.get("reason", "")),
            }
        )
    df = pd.DataFrame(rows)
    return df.sort_values(["date", "entry_id"], kind="mergesort").reset_index(drop=True)


def _cutoff_audit(reg: pd.DataFrame) -> pd.DataFrame:
    # late-arriving = posted_at exists and is in a later period than effective date
    def p(d: str) -> str:
        return d[:7] if d else ""

    df = reg.copy()
    df["posted_period"] = df["posted_at"].map(p)
    df["late_arrival"] = (df["posted_period"] != "") & (df["posted_period"] > df["period"])
    # compute days late where possible
    def days_late(row: pd.Series) -> str:
        if not row["posted_at"]:
            return ""
        try:
            eff = date.fromisoformat(str(row["date"]))
            post = date.fromisoformat(str(row["posted_at"]))
            return str((post - eff).days)
        except Exception:
            return ""
    df["days_late"] = df.apply(days_late, axis=1)
    return df.loc[df["kind"] == "adjustment", ["entry_id", "date", "period", "posted_at", "posted_period", "days_late", "late_arrival"]].reset_index(drop=True)


def _adjustment_deltas(tb_unadj: pd.DataFrame, tb_adj: pd.DataFrame) -> pd.DataFrame:
    a = tb_unadj.rename(columns={"balance": "unadjusted"})
    b = tb_adj.rename(columns={"balance": "adjusted"})
    m = pd.merge(a, b, on=["account", "root"], how="outer").fillna("0.00")
    m["delta"] = (m["adjusted"].map(_str_to_cents) - m["unadjusted"].map(_str_to_cents)).map(_cents_to_str)
    out = m[["account", "root", "unadjusted", "adjusted", "delta"]].sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def _resolve_outdir(outdir_root: str) -> Path:
    return Path(outdir_root) / "ch07"


# -------------------------
# Main
# -------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LedgerLoom Ch07: adjusting entries as late-arriving data")
    parser.add_argument("--outdir", default="outputs/ledgerloom", help="Output root directory")
    parser.add_argument("--seed", type=int, default=123, help="Seed (kept for API consistency; dataset is stable)")
    args = parser.parse_args(argv)

    outdir = _resolve_outdir(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base = _base_entries()
    adj = _adjusting_entries()
    all_entries = base + adj

    engine = LedgerEngine()
    postings_unadj = engine.postings_fact_table(base)
    postings_adj = engine.postings_fact_table(all_entries)

    tb_unadj = _trial_balance(postings_unadj)
    tb_adj = _trial_balance(postings_adj)

    is_unadj = _income_statement(tb_unadj)
    is_adj = _income_statement(tb_adj)

    bs_unadj = _balance_sheet_summary(tb_unadj)
    bs_adj = _balance_sheet_summary(tb_adj)

    reg = _entry_register(all_entries)
    reg_adj = reg.loc[reg["kind"] == "adjustment"].reset_index(drop=True)
    cutoff = _cutoff_audit(reg)
    deltas = _adjustment_deltas(tb_unadj, tb_adj)

    # invariants (engine + chapter-specific)
    inv_unadj = engine.invariants(base, postings_unadj)
    inv_adj = engine.invariants(all_entries, postings_adj)

    # Chapter invariant: the balance sheet equation should hold (Difference == 0.00)
    diff_unadj = str(bs_unadj.loc[bs_unadj["metric"] == "Difference", "amount"].iloc[0])
    diff_adj = str(bs_adj.loc[bs_adj["metric"] == "Difference", "amount"].iloc[0])

    invariants = {
        "engine_unadjusted": inv_unadj,
        "engine_adjusted": inv_adj,
        "chapter": {
            "equation_difference_unadjusted": diff_unadj,
            "equation_difference_adjusted": diff_adj,
            "late_arriving_adjustments": int(reg_adj.shape[0]),
        },
    }

    # Write artifacts
    artifacts: list[Path] = []

    def w_csv(name: str, df: pd.DataFrame) -> None:
        p = outdir / name
        write_csv_df(p, df)
        artifacts.append(p)

    def w_json(name: str, obj: Any) -> None:
        p = outdir / name
        write_json(p, obj)
        artifacts.append(p)

    w_csv("postings_unadjusted.csv", postings_unadj)
    w_csv("postings_adjusted.csv", postings_adj)
    w_csv("trial_balance_unadjusted.csv", tb_unadj)
    w_csv("trial_balance_adjusted.csv", tb_adj)
    w_csv("income_statement_unadjusted.csv", is_unadj)
    w_csv("income_statement_adjusted.csv", is_adj)
    w_csv("balance_sheet_unadjusted.csv", bs_unadj)
    w_csv("balance_sheet_adjusted.csv", bs_adj)
    w_csv("entry_register.csv", reg)
    w_csv("adjustments_register.csv", reg_adj)
    w_csv("cutoff_audit.csv", cutoff)
    w_csv("adjustment_deltas_by_account.csv", deltas)

    w_json("invariants.json", invariants)
    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        "chapter": "ch07_adjusting_entries_late_arriving_data",
        "seed": args.seed,
    }

    def _manifest_payload(d: Path) -> dict[str, object]:
        files = list(artifacts) + [d / "run_meta.json"]
        return {
            "artifacts": manifest_items(d, files, name_key="file"),
            "meta": {
                "chapter": "ch07",
                "seed": args.seed,
            },
        }

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    print(f"Wrote LedgerLoom Chapter 07 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

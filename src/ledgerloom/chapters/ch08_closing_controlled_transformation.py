"""LedgerLoom Chapter 08 — Closing as a controlled transformation.

Chapter 07 introduced *adjusting entries* as "late-arriving data":
you get an **unadjusted** close, then you append adjustments to produce an **adjusted** close.

Chapter 08 answers the next practical question:

    *How do we reset the temporary accounts (Revenue / Expenses) for the next period
    without losing the period's results?*

In accounting terms, this is **closing**.
In software-engineering terms, closing is a **controlled transformation**:

- It is *append-only*: we add closing entries; we never overwrite history.
- It is *deterministic*: given the adjusted trial balance, closing outputs are fully reproducible.
- It is *auditable*: we can prove that:
  - temporary accounts are zeroed
  - net income is transferred into Equity
  - the accounting equation still holds

This chapter uses the common **Income Summary** approach:

1) Close revenue into IncomeSummary
2) Close expenses into IncomeSummary
3) Close IncomeSummary into RetainedEarnings

Why IncomeSummary?
- It makes the transformation explicit and checkable (a "pipeline stage" with a clear invariant)
- It mirrors how batch systems materialize intermediate tables/views for correctness

Run:
  make ll-ch08
or:
  python -m ledgerloom.chapters.ch08_closing_controlled_transformation --outdir outputs/ledgerloom --seed 123
"""

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


"""I/O helpers are centralized in :mod:`ledgerloom.artifacts`."""


# -------------------------
# Money + period helpers
# -------------------------


def _str_to_cents(s: str) -> int:
    d = Decimal(str(s))
    return int((d * 100).to_integral_value())


def _cents_to_str(cents: int) -> str:
    q = Decimal(cents) / Decimal(100)
    return f"{q:.2f}"


def _period_from_iso_date(iso_date: str) -> str:
    # YYYY-MM-DD -> YYYY-MM
    return str(iso_date)[:7]


# -------------------------
# Scenario (same story as Ch07, then close it)
# -------------------------


def _make_entry(entry_id: str, dt: date, narration: str, lines: list[tuple[str, str, str]], meta: dict[str, Any]) -> Entry:
    postings: list[Posting] = []
    for acct, dr, cr in lines:
        postings.append(Posting(account=acct, debit=Decimal(dr), credit=Decimal(cr)))
    merged = {"entry_id": entry_id, **(meta or {})}
    return Entry(dt=dt, narration=narration, postings=postings, meta=merged)



def _base_entries() -> list[Entry]:
    """Unadjusted Jan close — recorded events as of the deadline."""
    return [
        _make_entry(
            "E0801",
            date(2026, 1, 2),
            "Owner contribution (cash)",
            [
                ("Assets:Cash", "5000.00", "0.00"),
                ("Equity:OwnerCapital", "0.00", "5000.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0802",
            date(2026, 1, 5),
            "Customer prepays for February service (recorded as revenue at receipt)",
            [
                ("Assets:Cash", "400.00", "0.00"),
                ("Revenue:Sales", "0.00", "400.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0803",
            date(2026, 1, 8),
            "Buy supplies on account",
            [
                ("Assets:Supplies", "300.00", "0.00"),
                ("Liabilities:AccountsPayable", "0.00", "300.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0804",
            date(2026, 1, 12),
            "Provide service on account (invoice customer)",
            [
                ("Assets:AccountsReceivable", "600.00", "0.00"),
                ("Revenue:Sales", "0.00", "600.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0805",
            date(2026, 1, 20),
            "Pay February rent in advance (recorded as expense)",
            [
                ("Expenses:Rent", "1000.00", "0.00"),
                ("Assets:Cash", "0.00", "1000.00"),
            ],
            {"department": "HQ", "entry_kind": "base"},
        ),
        _make_entry(
            "E0806",
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
    """Adjustments dated 2026-01-31, but posted after month-end."""
    eff = date(2026, 1, 31)
    return [
        _make_entry(
            "A0801",
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
                "posted_at": "2026-02-02",
                "prepared_by": "Controller",
                "source": "Customer contract",
                "reason": "Cash received in Jan relates to Feb service; revenue not yet earned.",
            },
        ),
        _make_entry(
            "A0802",
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
                "reason": "Rent paid in Jan covers February; classify as PrepaidRent (asset).",
            },
        ),
        _make_entry(
            "A0803",
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
            "A0804",
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
                "source": "Inventory count sheet",
                "reason": "Supplies consumed in Jan; adjust inventory to match count.",
            },
        ),
    ]


# -------------------------
# Derived views
# -------------------------


def _trial_balance(postings: pd.DataFrame) -> pd.DataFrame:
    cents = postings.assign(_c=postings["signed_delta"].map(_str_to_cents)).groupby("account", as_index=False)["_c"].sum()
    cents["root"] = cents["account"].map(lambda a: str(a).split(":", 1)[0])
    cents["balance"] = cents["_c"].map(_cents_to_str)
    out = cents[["account", "root", "balance"]].sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def _income_statement(tb: pd.DataFrame) -> pd.DataFrame:
    # signed balances are in "normal" orientation: revenue positive, expenses positive
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


def _balance_sheet_adjusted(tb: pd.DataFrame) -> pd.DataFrame:
    """Adjusted close: Revenue/Expenses still open, so include NetIncome to satisfy the equation."""
    def s(root: str) -> int:
        return int(tb.loc[tb["root"] == root, "balance"].map(_str_to_cents).sum())

    assets = s("Assets")
    liabilities = s("Liabilities")
    equity = s("Equity")
    ni = _str_to_cents(str(_income_statement(tb).loc[2, "amount"]))
    lhs = assets
    rhs = liabilities + equity + ni
    diff = lhs - rhs
    return pd.DataFrame(
        [
            {"metric": "Assets", "amount": _cents_to_str(assets)},
            {"metric": "Liabilities", "amount": _cents_to_str(liabilities)},
            {"metric": "Equity", "amount": _cents_to_str(equity)},
            {"metric": "NetIncome", "amount": _cents_to_str(ni)},
            {"metric": "EquationLHS_Assets", "amount": _cents_to_str(lhs)},
            {"metric": "EquationRHS_L+E+NI", "amount": _cents_to_str(rhs)},
            {"metric": "Difference", "amount": _cents_to_str(diff)},
        ]
    )


def _balance_sheet_post_close(tb: pd.DataFrame) -> pd.DataFrame:
    """Post-close: temporary accounts are zero, so the plain equation holds."""
    def s(root: str) -> int:
        return int(tb.loc[tb["root"] == root, "balance"].map(_str_to_cents).sum())

    assets = s("Assets")
    liabilities = s("Liabilities")
    equity = s("Equity")
    lhs = assets
    rhs = liabilities + equity
    diff = lhs - rhs
    return pd.DataFrame(
        [
            {"metric": "Assets", "amount": _cents_to_str(assets)},
            {"metric": "Liabilities", "amount": _cents_to_str(liabilities)},
            {"metric": "Equity", "amount": _cents_to_str(equity)},
            {"metric": "EquationLHS_Assets", "amount": _cents_to_str(lhs)},
            {"metric": "EquationRHS_L+E", "amount": _cents_to_str(rhs)},
            {"metric": "Difference", "amount": _cents_to_str(diff)},
        ]
    )


def _entry_register(entries: list[Entry]) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for e in entries:
        meta = dict(e.meta or {})
        rows.append(
            {
                "entry_id": str(meta.get("entry_id", "")),
                "date": e.dt.isoformat(),
                "narration": e.narration,
                "entry_kind": str(meta.get("entry_kind", "")),
                "affects_period": str(meta.get("affects_period", "")),
                "posted_at": str(meta.get("posted_at", "")),
                "prepared_by": str(meta.get("prepared_by", "")),
                "source": str(meta.get("source", "")),
                "reason": str(meta.get("reason", "")),
            }
        )
    return pd.DataFrame(rows).sort_values(["date", "entry_id"], kind="mergesort").reset_index(drop=True)


# -------------------------
# Closing logic (IncomeSummary approach)
# -------------------------


def _closing_entries_from_adjusted_tb(tb_adj: pd.DataFrame, period: str) -> list[Entry]:
    """Generate closing entries from an *adjusted* trial balance."""

    # balances in "normal orientation" (positive means normal)
    tmp_rev = tb_adj.loc[tb_adj["root"] == "Revenue"].copy()
    tmp_exp = tb_adj.loc[tb_adj["root"] == "Expenses"].copy()

    def nonzero(df: pd.DataFrame) -> pd.DataFrame:
        return df.loc[df["balance"].map(_str_to_cents) != 0].copy()

    tmp_rev = nonzero(tmp_rev)
    tmp_exp = nonzero(tmp_exp)

    # 1) Close revenue -> IncomeSummary (debit revenue, credit income summary)
    rev_total = int(tmp_rev["balance"].map(_str_to_cents).sum())
    rev_lines: list[tuple[str, str, str]] = []
    for _, r in tmp_rev.iterrows():
        amt = _cents_to_str(_str_to_cents(str(r["balance"])))
        rev_lines.append((str(r["account"]), amt, "0.00"))  # debit revenue
    rev_lines.append(("Equity:IncomeSummary", "0.00", _cents_to_str(rev_total)))  # credit income summary
    e_rev = _make_entry(
        "C0801",
        date(2026, 1, 31),
        "Close revenue to IncomeSummary",
        rev_lines,
        {
            "department": "HQ",
            "entry_kind": "closing",
            "affects_period": period,
            "posted_at": "2026-02-06",
            "prepared_by": "Controller",
            "source": "Adjusted trial balance",
            "reason": "Reset revenue accounts to 0 and transfer totals to IncomeSummary.",
        },
    )

    # 2) Close expenses -> IncomeSummary (credit expenses, debit income summary)
    exp_total = int(tmp_exp["balance"].map(_str_to_cents).sum())
    exp_lines: list[tuple[str, str, str]] = []
    exp_lines.append(("Equity:IncomeSummary", _cents_to_str(exp_total), "0.00"))  # debit income summary
    for _, r in tmp_exp.iterrows():
        amt = _cents_to_str(_str_to_cents(str(r["balance"])))
        exp_lines.append((str(r["account"]), "0.00", amt))  # credit expense
    e_exp = _make_entry(
        "C0802",
        date(2026, 1, 31),
        "Close expenses to IncomeSummary",
        exp_lines,
        {
            "department": "HQ",
            "entry_kind": "closing",
            "affects_period": period,
            "posted_at": "2026-02-06",
            "prepared_by": "Controller",
            "source": "Adjusted trial balance",
            "reason": "Reset expense accounts to 0 and transfer totals to IncomeSummary.",
        },
    )

    # Net income (Revenue - Expenses)
    ni = rev_total - exp_total

    # 3) Close IncomeSummary -> RetainedEarnings
    if ni >= 0:
        lines = [
            ("Equity:IncomeSummary", _cents_to_str(ni), "0.00"),  # debit (zero out credit balance)
            ("Equity:RetainedEarnings", "0.00", _cents_to_str(ni)),  # credit
        ]
        narration = "Close IncomeSummary (net income) to RetainedEarnings"
    else:
        loss = -ni
        lines = [
            ("Equity:IncomeSummary", "0.00", _cents_to_str(loss)),  # credit (zero out debit balance)
            ("Equity:RetainedEarnings", _cents_to_str(loss), "0.00"),  # debit
        ]
        narration = "Close IncomeSummary (net loss) to RetainedEarnings"

    e_is = _make_entry(
        "C0803",
        date(2026, 1, 31),
        narration,
        lines,
        {
            "department": "HQ",
            "entry_kind": "closing",
            "affects_period": period,
            "posted_at": "2026-02-06",
            "prepared_by": "Controller",
            "source": "IncomeSummary balance",
            "reason": "Transfer net income to permanent equity (RetainedEarnings).",
        },
    )

    return [e_rev, e_exp, e_is]


def _temp_account_balances(tb_before: pd.DataFrame, tb_after: pd.DataFrame) -> pd.DataFrame:
    before = tb_before.copy()
    after = tb_after.copy()
    before = before.loc[before["root"].isin(["Revenue", "Expenses", "Equity"])].copy()
    after = after.loc[after["root"].isin(["Revenue", "Expenses", "Equity"])].copy()

    # Only equity rows that are part of closing story
    keep_equity = {"Equity:IncomeSummary", "Equity:RetainedEarnings"}
    before = before.loc[(before["root"] != "Equity") | (before["account"].isin(keep_equity))].copy()
    after = after.loc[(after["root"] != "Equity") | (after["account"].isin(keep_equity))].copy()

    merged = before.merge(after[["account", "balance"]], on="account", how="outer", suffixes=("_before", "_after"))
    merged["root"] = merged["account"].map(lambda a: str(a).split(":", 1)[0])
    merged["balance_before"] = merged["balance_before"].fillna("0.00")
    merged["balance_after"] = merged["balance_after"].fillna("0.00")
    merged = merged[["account", "root", "balance_before", "balance_after"]].sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return merged


def _equity_rollforward(tb_before: pd.DataFrame, tb_after: pd.DataFrame) -> pd.DataFrame:
    def s(tb: pd.DataFrame) -> int:
        return int(tb.loc[tb["root"] == "Equity", "balance"].map(_str_to_cents).sum())

    eq_before = s(tb_before)
    eq_after = s(tb_after)
    ni = _str_to_cents(str(_income_statement(tb_before).loc[2, "amount"]))
    return pd.DataFrame(
        [
            {"metric": "Equity_BeforeClosing", "amount": _cents_to_str(eq_before)},
            {"metric": "NetIncome_Transferred", "amount": _cents_to_str(ni)},
            {"metric": "Equity_AfterClosing", "amount": _cents_to_str(eq_after)},
            {"metric": "Check_EqAfter_minus_EqBefore", "amount": _cents_to_str(eq_after - eq_before)},
        ]
    )


def _resolve_outdir(outroot: str) -> Path:
    root = Path(outroot)
    if root.name != "ch08":
        root = root / "ch08"
    return root


# -------------------------
# Main
# -------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LedgerLoom Ch08: closing as a controlled transformation (IncomeSummary)")
    parser.add_argument("--outdir", default="outputs/ledgerloom", help="Output root directory")
    parser.add_argument("--seed", type=int, default=123, help="Seed (kept for API consistency; dataset is stable)")
    args = parser.parse_args(argv)

    outdir = _resolve_outdir(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base = _base_entries()
    adj = _adjusting_entries()
    adjusted_entries = base + adj

    engine = LedgerEngine()
    postings_adj = engine.postings_fact_table(adjusted_entries)
    tb_adj = _trial_balance(postings_adj)
    is_adj = _income_statement(tb_adj)
    bs_adj = _balance_sheet_adjusted(tb_adj)

    period = "2026-01"
    closing = _closing_entries_from_adjusted_tb(tb_adj, period)
    post_close_entries = adjusted_entries + closing

    postings_post = engine.postings_fact_table(post_close_entries)
    tb_post = _trial_balance(postings_post)
    is_post = _income_statement(tb_post)
    bs_post = _balance_sheet_post_close(tb_post)

    # Registers / diagnostics
    reg_closing = _entry_register(closing)
    postings_closing = engine.postings_fact_table(closing)
    temp_bal = _temp_account_balances(tb_adj, tb_post)
    eq_rf = _equity_rollforward(tb_adj, tb_post)

    # Checks (chapter-level invariants)
    def cents0(x: str) -> bool:
        return _str_to_cents(x) == 0

    # Revenue + expense accounts must be zero after close
    post_tmp = tb_post.loc[tb_post["root"].isin(["Revenue", "Expenses"])].copy()
    tmp_zero = bool((post_tmp["balance"].map(_str_to_cents) == 0).all())

    # IncomeSummary must be zero
    is_row = tb_post.loc[tb_post["account"] == "Equity:IncomeSummary"]
    income_summary_zero = True
    if not is_row.empty:
        income_summary_zero = cents0(str(is_row.iloc[0]["balance"]))

    # Equity rollforward check
    eq_check = _str_to_cents(str(eq_rf.loc[3, "amount"])) == _str_to_cents(str(eq_rf.loc[1, "amount"]))

    inv_adj = engine.invariants(adjusted_entries, postings_adj)
    inv_post = engine.invariants(post_close_entries, postings_post)

    diff_adj = _str_to_cents(str(bs_adj.loc[6, "amount"]))
    diff_post = _str_to_cents(str(bs_post.loc[5, "amount"]))

    checklist = {
        "period": period,
        "temporary_accounts_zeroed": tmp_zero,
        "income_summary_zeroed": income_summary_zero,
        "equity_increased_by_net_income": eq_check,
        "equation_difference_adjusted_cents": int(diff_adj),
        "equation_difference_post_close_cents": int(diff_post),
        "engine_invariants_adjusted_ok": bool(inv_adj.get("all_ok", False)),
        "engine_invariants_post_close_ok": bool(inv_post.get("all_ok", False)),
    }

    invariants = {
        "engine_adjusted": inv_adj,
        "engine_post_close": inv_post,
        "chapter": {
            "temporary_accounts_zeroed": tmp_zero,
            "income_summary_zeroed": income_summary_zero,
            "equity_increased_by_net_income": eq_check,
            "equation_difference_adjusted_cents": int(diff_adj),
            "equation_difference_post_close_cents": int(diff_post),
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

    w_csv("postings_adjusted.csv", postings_adj)
    w_csv("postings_closing.csv", postings_closing)
    w_csv("postings_post_close.csv", postings_post)

    w_csv("trial_balance_adjusted.csv", tb_adj)
    w_csv("trial_balance_post_close.csv", tb_post)

    w_csv("income_statement_adjusted.csv", is_adj)
    w_csv("income_statement_post_close.csv", is_post)

    w_csv("balance_sheet_adjusted.csv", bs_adj)
    w_csv("balance_sheet_post_close.csv", bs_post)

    w_csv("closing_entries_register.csv", reg_closing)
    w_csv("temp_accounts_before_after.csv", temp_bal)
    w_csv("equity_rollforward.csv", eq_rf)

    w_json("closing_checklist.json", checklist)
    w_json("invariants.json", invariants)

    run_meta = {"chapter": "ch08", "module": "ledgerloom.chapters.ch08_closing_controlled_transformation", "seed": args.seed}
    def _manifest_payload(d: Path) -> dict[str, object]:
        files = artifacts + [d / "run_meta.json"]
        return {"artifacts": manifest_items(d, files, name_key="file"), "meta": {"chapter": "ch08", "seed": args.seed}}

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    print(f"Wrote LedgerLoom Chapter 08 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

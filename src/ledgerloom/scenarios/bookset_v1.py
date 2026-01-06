"""Scenario helpers for the LedgerLoom bookset (v1).

Why this module exists
----------------------
Later chapters (Ch10+) should not import private helpers from earlier chapter
modules. Chapters are runnable scripts; they are not meant to be a shared
library.

This module provides a *public, stable* scenario layer that chapters can share:

- A deterministic "bookset" dataset (base + adjusting entries)
- A post-close snapshot (postings + trial balance + statements)
- An opening-entry constructor (carry-forward balances)

The implementation intentionally mirrors the Chapter 08 logic so existing
chapter outputs remain byte-for-byte stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine
from ledgerloom.engine.config import LedgerEngineConfig
from ledgerloom.engine.money import cents_to_str, str_to_cents


@dataclass(frozen=True)
class PostCloseSnapshot:
    """Outputs of the bookset close process.

    This is the canonical payload that later chapters should consume instead of
    reaching into Chapter 08 internals.
    """

    period: str
    close_date: date

    adjusted_entries: list[Entry]
    closing_entries: list[Entry]
    post_close_entries: list[Entry]

    postings_adjusted: pd.DataFrame
    postings_post_close: pd.DataFrame

    trial_balance_adjusted: pd.DataFrame
    trial_balance_post_close: pd.DataFrame

    income_statement_adjusted: pd.DataFrame
    balance_sheet_adjusted: pd.DataFrame
    balance_sheet_post_close: pd.DataFrame


def compute_post_close_snapshot(
    *,
    cfg: LedgerEngineConfig | None = None,
    period: str = "2026-01",
    close_date: date = date(2026, 1, 31),
) -> PostCloseSnapshot:
    """Compute the bookset post-close snapshot.

    Parameters
    ----------
    cfg:
        Engine configuration (normal balances, entry_id policy, etc.).
    period:
        Accounting period label used in closing entry metadata.
    close_date:
        Date used on the closing entries.
    """

    if cfg is None:
        cfg = LedgerEngineConfig()

    engine = LedgerEngine(cfg=cfg)

    base = _base_entries()
    adj = _adjusting_entries()
    adjusted_entries = base + adj

    postings_adj = engine.postings_fact_table(adjusted_entries)
    tb_adj = trial_balance(postings_adj)
    is_adj = income_statement(tb_adj)
    bs_adj = balance_sheet_adjusted(tb_adj)

    closing = closing_entries_from_adjusted_tb(tb_adj, period=period, close_date=close_date)
    post_close_entries = adjusted_entries + closing

    postings_post = engine.postings_fact_table(post_close_entries)
    tb_post = trial_balance(postings_post)
    bs_post = balance_sheet_post_close(tb_post)

    return PostCloseSnapshot(
        period=period,
        close_date=close_date,
        adjusted_entries=adjusted_entries,
        closing_entries=closing,
        post_close_entries=post_close_entries,
        postings_adjusted=postings_adj,
        postings_post_close=postings_post,
        trial_balance_adjusted=tb_adj,
        trial_balance_post_close=tb_post,
        income_statement_adjusted=is_adj,
        balance_sheet_adjusted=bs_adj,
        balance_sheet_post_close=bs_post,
    )


def compute_opening_from_post_close(
    *,
    tb_post_close: pd.DataFrame,
    opening_date: date,
    cfg: LedgerEngineConfig | None = None,
    entry_id: str = "OPEN-2026-02-01",
    narration: str = "Opening balance carry-forward (from Ch08 post-close)",
    meta: dict[str, str] | None = None,
) -> Entry:
    """Build an opening entry that carries forward balances.

    The opening entry carries forward all non-zero Assets, Liabilities, and
    Equity balances from the provided post-close trial balance.
    """

    if cfg is None:
        cfg = LedgerEngineConfig()

    tb = tb_post_close.copy()
    tb = tb.loc[tb["root"].isin(["Assets", "Liabilities", "Equity"])].copy()
    tb["balance_cents"] = tb["balance"].map(str_to_cents)
    tb = tb.loc[tb["balance_cents"] != 0].copy()

    # Stable order (mirrors Chapter 08/08.5): Assets, Liabilities, Equity; then account.
    root_order = {"Assets": 0, "Liabilities": 1, "Equity": 2}
    tb["root_order"] = tb["root"].map(root_order)
    tb = tb.sort_values(["root_order", "account"], kind="mergesort").reset_index(drop=True)

    postings: list[Posting] = []
    total_debits = 0
    total_credits = 0

    for _, r in tb.iterrows():
        acct = str(r["account"])
        root = str(r["root"])
        bal = int(r["balance_cents"])  # normal-orientation balance

        # Convert a normal-orientation balance into a debit/credit amount.
        # Positive balance means the account has its normal side.
        if root in cfg.debit_normal_roots:
            if bal > 0:
                dr = bal
                cr = 0
            else:
                dr = 0
                cr = -bal
        elif root in cfg.credit_normal_roots:
            if bal > 0:
                dr = 0
                cr = bal
            else:
                dr = -bal
                cr = 0
        else:
            raise ValueError(f"Unknown root for opening balance logic: {root}")

        if dr:
            postings.append(Posting(acct, debit=Decimal(cents_to_str(dr)), credit=Decimal("0")))
        else:
            postings.append(Posting(acct, debit=Decimal("0"), credit=Decimal(cents_to_str(cr))))

        total_debits += dr
        total_credits += cr

    if total_debits != total_credits:
        raise ValueError(
            "Opening entry is not balanced "
            f"(debits={cents_to_str(total_debits)}, credits={cents_to_str(total_credits)})"
        )

    meta_out = {"entry_id": entry_id}
    if meta:
        meta_out.update(meta)

    e = Entry(dt=opening_date, narration=narration, postings=postings, meta=meta_out)
    e.validate_balanced()
    return e


# -----------------------------------------------------------------------------
# Shared report helpers (mirrors Ch08)
# -----------------------------------------------------------------------------


def trial_balance(postings: pd.DataFrame) -> pd.DataFrame:
    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(str_to_cents)

    g = tmp.groupby(["account", "root"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(cents_to_str)
    # Match Chapter 08's trial balance CSV contract: account, root, balance.
    out = g[["account", "root", "balance"]]
    out = out.sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def income_statement(tb: pd.DataFrame) -> pd.DataFrame:
    """Income statement from a trial balance (Revenue/Expenses only)."""

    rev = int(tb.loc[tb["root"] == "Revenue", "balance"].map(str_to_cents).sum())
    exp = int(tb.loc[tb["root"] == "Expenses", "balance"].map(str_to_cents).sum())
    ni = rev - exp
    return pd.DataFrame(
        [
            {"metric": "Revenue", "amount": cents_to_str(rev)},
            {"metric": "Expenses", "amount": cents_to_str(exp)},
            {"metric": "NetIncome", "amount": cents_to_str(ni)},
        ]
    )


def balance_sheet_adjusted(tb: pd.DataFrame) -> pd.DataFrame:
    """Adjusted close: Revenue/Expenses still open, so include NetIncome."""

    def s(root: str) -> int:
        return int(tb.loc[tb["root"] == root, "balance"].map(str_to_cents).sum())

    assets = s("Assets")
    liabilities = s("Liabilities")
    equity = s("Equity")
    ni = str_to_cents(str(income_statement(tb).loc[2, "amount"]))
    lhs = assets
    rhs = liabilities + equity + ni
    diff = lhs - rhs
    return pd.DataFrame(
        [
            {"metric": "Assets", "amount": cents_to_str(assets)},
            {"metric": "Liabilities", "amount": cents_to_str(liabilities)},
            {"metric": "Equity", "amount": cents_to_str(equity)},
            {"metric": "NetIncome", "amount": cents_to_str(ni)},
            {"metric": "EquationLHS_Assets", "amount": cents_to_str(lhs)},
            {"metric": "EquationRHS_L+E+NI", "amount": cents_to_str(rhs)},
            {"metric": "Difference", "amount": cents_to_str(diff)},
        ]
    )


def balance_sheet_post_close(tb: pd.DataFrame) -> pd.DataFrame:
    """Post-close: temporary accounts are zero, so the plain equation holds."""

    def s(root: str) -> int:
        return int(tb.loc[tb["root"] == root, "balance"].map(str_to_cents).sum())

    assets = s("Assets")
    liabilities = s("Liabilities")
    equity = s("Equity")
    lhs = assets
    rhs = liabilities + equity
    diff = lhs - rhs
    return pd.DataFrame(
        [
            {"metric": "Assets", "amount": cents_to_str(assets)},
            {"metric": "Liabilities", "amount": cents_to_str(liabilities)},
            {"metric": "Equity", "amount": cents_to_str(equity)},
            {"metric": "EquationLHS_Assets", "amount": cents_to_str(lhs)},
            {"metric": "EquationRHS_L+E", "amount": cents_to_str(rhs)},
            {"metric": "Difference", "amount": cents_to_str(diff)},
        ]
    )


def closing_entries_from_adjusted_tb(
    tb_adj: pd.DataFrame,
    *,
    period: str,
    close_date: date,
) -> list[Entry]:
    """Generate closing entries from an *adjusted* trial balance."""

    tmp_rev = tb_adj.loc[tb_adj["root"] == "Revenue"].copy()
    tmp_exp = tb_adj.loc[tb_adj["root"] == "Expenses"].copy()

    def nonzero(df: pd.DataFrame) -> pd.DataFrame:
        return df.loc[df["balance"].map(str_to_cents) != 0].copy()

    tmp_rev = nonzero(tmp_rev)
    tmp_exp = nonzero(tmp_exp)

    # 1) Close revenue -> IncomeSummary (debit revenue, credit income summary)
    rev_total = int(tmp_rev["balance"].map(str_to_cents).sum())
    rev_lines: list[tuple[str, str, str]] = []
    for _, r in tmp_rev.iterrows():
        amt = cents_to_str(str_to_cents(str(r["balance"])))
        rev_lines.append((str(r["account"]), amt, "0.00"))
    rev_lines.append(("Equity:IncomeSummary", "0.00", cents_to_str(rev_total)))
    e_rev = _make_entry(
        "C0801",
        close_date,
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
    exp_total = int(tmp_exp["balance"].map(str_to_cents).sum())
    exp_lines: list[tuple[str, str, str]] = []
    exp_lines.append(("Equity:IncomeSummary", cents_to_str(exp_total), "0.00"))
    for _, r in tmp_exp.iterrows():
        amt = cents_to_str(str_to_cents(str(r["balance"])))
        exp_lines.append((str(r["account"]), "0.00", amt))
    e_exp = _make_entry(
        "C0802",
        close_date,
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
            ("Equity:IncomeSummary", cents_to_str(ni), "0.00"),
            ("Equity:RetainedEarnings", "0.00", cents_to_str(ni)),
        ]
        narration = "Close IncomeSummary (net income) to RetainedEarnings"
    else:
        loss = -ni
        lines = [
            ("Equity:IncomeSummary", "0.00", cents_to_str(loss)),
            ("Equity:RetainedEarnings", cents_to_str(loss), "0.00"),
        ]
        narration = "Close IncomeSummary (net loss) to RetainedEarnings"

    e_is = _make_entry(
        "C0803",
        close_date,
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


# -----------------------------------------------------------------------------
# Bookset dataset (copied from Ch08 verbatim; stable teaching fixture)
# -----------------------------------------------------------------------------


def _make_entry(
    entry_id: str,
    dt: date,
    narration: str,
    lines: list[tuple[str, str, str]],
    meta: dict[str, str] | None = None,
) -> Entry:
    postings: list[Posting] = []
    for acct, dr, cr in lines:
        dr_d = Decimal(dr)
        cr_d = Decimal(cr)
        postings.append(Posting(acct, debit=dr_d, credit=cr_d))
    m: dict[str, str] = {"entry_id": entry_id}
    if meta:
        m.update(meta)
    e = Entry(dt=dt, narration=narration, postings=postings, meta=m)
    e.validate_balanced()
    return e


def _base_entries() -> list[Entry]:
    """Unadjusted Jan close — recorded events as of the deadline.

    Copied from :mod:`ledgerloom.chapters.ch08_closing_controlled_transformation`.
    """

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
    """Adjustments dated 2026-01-31, but posted after month-end.

    Copied from :mod:`ledgerloom.chapters.ch08_closing_controlled_transformation`.
    """

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


__all__ = [
    "PostCloseSnapshot",
    "compute_post_close_snapshot",
    "compute_opening_from_post_close",
    "trial_balance",
    "income_statement",
    "balance_sheet_adjusted",
    "balance_sheet_post_close",
    "closing_entries_from_adjusted_tb",
]

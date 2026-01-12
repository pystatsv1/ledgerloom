"""Closing entries (workbook + engine helper).

This module provides a small, *pure* helper that turns an adjusted trial
balance into closing :class:`ledgerloom.core.Entry` objects.

Design goals (PR-E3a):
- Sign-safe: supports negative / contra balances.
- Zero-safe: never emits 0/0 posting lines.
- Workbook-friendly: does **not** require an IncomeSummary account.

Input contract
-------------
``tb_adj`` must be a DataFrame with columns: ``account``, ``root``, ``balance``.

Balance convention
-----------------
LedgerLoom trial balance balances use the engine's *normal* sign convention:

- debit-normal roots (Assets, Expenses): ``balance = debits - credits``
- credit-normal roots (Liabilities, Equity, Revenue): ``balance = credits - debits``

This means a negative balance indicates an "abnormal" side (e.g., a
refund/contra-revenue).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.engine.config import LedgerEngineConfig
from ledgerloom.engine.money import cents_to_str, str_to_cents


def closing_entries_from_adjusted_tb(
    tb_adj: pd.DataFrame,
    *,
    period: str,
    close_date: date,
) -> list[Entry]:
    """Generate closing entries from an adjusted trial balance.

    Returns a list of :class:`~ledgerloom.core.Entry` objects.

    Closing policy (workbook-friendly):
    - Revenue accounts close directly to Retained Earnings.
    - Expense accounts close directly to Retained Earnings.
    - Dividend/Draw accounts (identified by account name) close to Retained Earnings.

    The helper is deterministic:
    - stable entry_ids
    - stable account ordering inside each entry
    """

    required = {"account", "root", "balance"}
    missing = required - set(tb_adj.columns)
    if missing:
        raise ValueError("tb_adj missing required columns: " + ", ".join(sorted(missing)))

    cfg = LedgerEngineConfig()

    tb = tb_adj.copy()
    tb["account"] = tb["account"].astype(str)
    tb["root"] = tb["root"].astype(str)
    tb["balance_cents"] = tb["balance"].astype(str).map(str_to_cents)

    def is_dividends_account(acct: str) -> bool:
        leaf = acct.split(":")[-1].lower()
        return "dividend" in leaf or "draw" in leaf

    out: list[Entry] = []

    # Revenue (temporary) -> Retained Earnings
    out.extend(
        _close_accounts_to_retained_earnings(
            tb,
            root="Revenue",
            entry_id=f"closing:{period}:revenue",
            narration="Close revenue to RetainedEarnings",
            close_date=close_date,
            period=period,
            cfg=cfg,
        )
    )

    # Expenses (temporary) -> Retained Earnings
    out.extend(
        _close_accounts_to_retained_earnings(
            tb,
            root="Expenses",
            entry_id=f"closing:{period}:expenses",
            narration="Close expenses to RetainedEarnings",
            close_date=close_date,
            period=period,
            cfg=cfg,
        )
    )

    # Dividends / Draws (temporary equity) -> Retained Earnings
    div = tb.loc[(tb["root"] == "Equity") & tb["account"].map(is_dividends_account)].copy()
    if not div.empty:
        out.extend(
            _close_df_to_retained_earnings(
                div,
                entry_id=f"closing:{period}:dividends",
                narration="Close dividends/draws to RetainedEarnings",
                close_date=close_date,
                period=period,
                cfg=cfg,
            )
        )

    return out


def _close_accounts_to_retained_earnings(
    tb: pd.DataFrame,
    *,
    root: str,
    entry_id: str,
    narration: str,
    close_date: date,
    period: str,
    cfg: LedgerEngineConfig,
) -> list[Entry]:
    df = tb.loc[tb["root"] == root].copy()
    return _close_df_to_retained_earnings(
        df,
        entry_id=entry_id,
        narration=narration,
        close_date=close_date,
        period=period,
        cfg=cfg,
    )


def _close_df_to_retained_earnings(
    df: pd.DataFrame,
    *,
    entry_id: str,
    narration: str,
    close_date: date,
    period: str,
    cfg: LedgerEngineConfig,
) -> list[Entry]:
    df = df.loc[df["balance_cents"] != 0].copy()
    if df.empty:
        return []

    # Deterministic order: root then account name.
    df = df.sort_values(["root", "account"], kind="mergesort")

    postings: list[Posting] = []
    total_debits_cents = 0
    total_credits_cents = 0

    for _, r in df.iterrows():
        acct = str(r["account"])
        root = str(r["root"])
        bal = int(r["balance_cents"])
        p = _posting_to_zero_balance(cfg=cfg, root=root, account=acct, balance_cents=bal)
        if p is None:
            continue
        postings.append(p)
        total_debits_cents += str_to_cents(str(p.debit))
        total_credits_cents += str_to_cents(str(p.credit))

    if not postings:
        return []

    # Add balancing line to Retained Earnings, if needed.
    diff = total_debits_cents - total_credits_cents
    if diff > 0:
        postings.append(
            Posting(
                account="Equity:RetainedEarnings",
                debit=Decimal("0"),
                credit=Decimal(cents_to_str(diff)),
            )
        )
    elif diff < 0:
        postings.append(
            Posting(
                account="Equity:RetainedEarnings",
                debit=Decimal(cents_to_str(-diff)),
                credit=Decimal("0"),
            )
        )

    e = Entry(
        dt=close_date,
        narration=narration,
        postings=postings,
        meta={
            "entry_id": entry_id,
            "entry_kind": "closing",
            "affects_period": period,
        },
    )
    e.validate_balanced()
    return [e]


def _posting_to_zero_balance(
    *,
    cfg: LedgerEngineConfig,
    root: str,
    account: str,
    balance_cents: int,
) -> Posting | None:
    """Return a single posting line that moves an account's balance to zero."""

    if balance_cents == 0:
        return None

    # Balance is expressed in the engine's normal sign convention.
    # To zero the account, we post the opposite side implied by the sign.
    if root in cfg.debit_normal_roots:
        # Positive => debit balance. Close by CREDIT.
        if balance_cents > 0:
            return Posting(account=account, debit=Decimal("0"), credit=Decimal(cents_to_str(balance_cents)))
        # Negative => credit balance. Close by DEBIT.
        return Posting(account=account, debit=Decimal(cents_to_str(-balance_cents)), credit=Decimal("0"))

    # Credit-normal roots: Positive => credit balance. Close by DEBIT.
    if balance_cents > 0:
        return Posting(account=account, debit=Decimal(cents_to_str(balance_cents)), credit=Decimal("0"))
    # Negative => debit balance. Close by CREDIT.
    return Posting(account=account, debit=Decimal("0"), credit=Decimal(cents_to_str(-balance_cents)))

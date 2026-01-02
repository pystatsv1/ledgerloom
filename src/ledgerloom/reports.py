from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable

from .chart import ASSET, EQUITY, EXPENSE, INCOME, LIAB, account_root, signed_delta
from .core import Entry


def trial_balance(entries: Iterable[Entry]) -> Dict[str, Decimal]:
    """Aggregate entries into account balances, validating the double-entry invariant."""
    bal: Dict[str, Decimal] = {}
    for e in entries:
        e.validate_balanced()
        for p in e.postings:
            d = signed_delta(p.account, p.debit, p.credit)
            bal[p.account] = bal.get(p.account, Decimal("0")) + d
    return dict(sorted(bal.items()))


def income_statement(bal: Dict[str, Decimal]) -> Dict[str, Decimal]:
    income = sum(v for a, v in bal.items() if account_root(a) == INCOME)
    expense = sum(v for a, v in bal.items() if account_root(a) == EXPENSE)
    return {"Income": income, "Expenses": expense, "NetIncome": income - expense}


def balance_sheet(bal: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Return a balance sheet that includes net income (i.e., equity after closing).

    If you don't explicitly post a closing entry, income/expense accounts are still
    "open". For the accounting equation to hold, net income must be treated as an
    increase to equity (retained earnings).
    """
    assets = sum(v for a, v in bal.items() if account_root(a) == ASSET)
    liab = sum(v for a, v in bal.items() if account_root(a) == LIAB)
    eq = sum(v for a, v in bal.items() if account_root(a) == EQUITY)

    is_ = income_statement(bal)
    ni = is_["NetIncome"]

    eq_after_close = eq + ni

    return {
        "Assets": assets,
        "Liabilities": liab,
        "Equity": eq,
        "NetIncome": ni,
        "EquityAfterClose": eq_after_close,
        "Check": assets - (liab + eq_after_close),
    }

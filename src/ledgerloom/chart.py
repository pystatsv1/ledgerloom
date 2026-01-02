from __future__ import annotations

from decimal import Decimal

ASSET = "Assets"
LIAB = "Liabilities"
EQUITY = "Equity"
INCOME = "Income"
EXPENSE = "Expenses"

NORMAL_DEBIT = {ASSET, EXPENSE}
NORMAL_CREDIT = {LIAB, EQUITY, INCOME}


def account_root(account: str) -> str:
    """Return the root of an account name: 'Assets:Cash' -> 'Assets'."""
    return account.split(":", 1)[0]


def signed_delta(account: str, debit: Decimal, credit: Decimal) -> Decimal:
    """Return a dev-friendly signed delta (type-aware sign convention).

    Assets/Expenses: debit increases (+), credit decreases (-)
    Liabilities/Equity/Income: credit increases (+), debit decreases (-)
    """
    root = account_root(account)
    if root in NORMAL_DEBIT:
        return debit - credit
    if root in NORMAL_CREDIT:
        return credit - debit
    raise ValueError(f"Unknown account root '{root}' for account '{account}'")

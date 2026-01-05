"""Chart helpers.

LedgerLoom uses colon-path account names like ``Assets:Cash``.

For the foundations chapters we keep the chart model deliberately simple:

- The *root* is the first segment before ``:``.
- The root defines the normal-balance sign convention used for signed amounts.

Normal-balance conventions (developer-friendly encoding):

- **Assets / Expenses**: debit increases (+), credit decreases (-)
- **Liabilities / Equity / Revenue**: credit increases (+), debit decreases (-)

The engine (``ledgerloom.engine``) uses the same root conventions; this module
exists mostly for early chapters and small helpers.
"""

from __future__ import annotations

from decimal import Decimal

ASSET = "Assets"
LIAB = "Liabilities"
EQUITY = "Equity"
REVENUE = "Revenue"
EXPENSE = "Expenses"

DEBIT_NORMAL_ROOTS = {ASSET, EXPENSE}
CREDIT_NORMAL_ROOTS = {LIAB, EQUITY, REVENUE}


def account_root(account: str) -> str:
    return account.split(":", 1)[0]


def signed_delta(account: str, debit: Decimal, credit: Decimal) -> Decimal:
    """Return a signed amount using the root's normal balance.

    - Debit-normal roots: debit - credit
    - Credit-normal roots: credit - debit

    If the root is unknown, we fall back to debit-normal.
    """

    root = account_root(account)
    if root in DEBIT_NORMAL_ROOTS:
        return debit - credit
    if root in CREDIT_NORMAL_ROOTS:
        return credit - debit
    return debit - credit

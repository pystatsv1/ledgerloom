from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable

from .core import Entry
from .engine import LedgerEngine


def _root(account: str) -> str:
    return account.split(":", 1)[0]


def trial_balance(entries: Iterable[Entry]) -> Dict[str, Decimal]:
    """Aggregate entries into account balances (signed amounts).

    Implementation note:
    We compile entries into postings using the LedgerLoom Engine so that *all*
    sign conventions live in one place (Assets/Expenses debit-normal; others
    credit-normal).
    """

    es = list(entries)
    for e in es:
        e.validate_balanced()

    engine = LedgerEngine()
    postings = engine.postings_fact_table(es)

    bal: Dict[str, Decimal] = {}
    # signed_delta is stored as a canonical string like "123.45".
    for _, row in postings.iterrows():
        acct = str(row["account"])
        d = Decimal(str(row["signed_delta"]))
        bal[acct] = bal.get(acct, Decimal("0")) + d

    return dict(sorted(bal.items()))


def income_statement(bal: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Return a simple income statement (Revenue, Expenses, NetIncome)."""

    revenue = sum(v for a, v in bal.items() if _root(a) == "Revenue")
    expense = sum(v for a, v in bal.items() if _root(a) == "Expenses")
    return {"Revenue": revenue, "Expenses": expense, "NetIncome": revenue - expense}


def balance_sheet(bal: Dict[str, Decimal]) -> Dict[str, Decimal]:
    """Return a balance sheet that includes net income (i.e., equity after closing).

    If you don't explicitly post a closing entry, revenue/expense accounts are still
    "open". For the accounting equation to hold, net income must be treated as an
    increase to equity (retained earnings).
    """

    assets = sum(v for a, v in bal.items() if _root(a) == "Assets")
    liab = sum(v for a, v in bal.items() if _root(a) == "Liabilities")
    eq = sum(v for a, v in bal.items() if _root(a) == "Equity")

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

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd

from ledgerloom.engine import closing_entries_from_adjusted_tb


def _tb(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["account", "root", "balance"])


def _find_posting(e, account: str):
    for p in e.postings:
        if p.account == account:
            return p
    raise AssertionError(f"posting for account not found: {account}")


def test_closing_entries_normal_case() -> None:
    tb_adj = _tb(
        [
            {"account": "Revenue:Sales", "root": "Revenue", "balance": "1000.00"},
            {"account": "Expenses:Rent", "root": "Expenses", "balance": "400.00"},
            {"account": "Assets:Cash", "root": "Assets", "balance": "600.00"},
        ]
    )

    close = closing_entries_from_adjusted_tb(tb_adj, period="2026-01", close_date=date(2026, 1, 31))
    assert len(close) == 2

    rev_entry = close[0]
    exp_entry = close[1]
    assert rev_entry.meta.get("entry_kind") == "closing"
    assert exp_entry.meta.get("entry_kind") == "closing"

    # Revenue (credit-normal) closes by DEBITing revenue and CREDITing retained earnings.
    p_sales = _find_posting(rev_entry, "Revenue:Sales")
    assert p_sales.debit == Decimal("1000.00")
    assert p_sales.credit == Decimal("0")
    p_re = _find_posting(rev_entry, "Equity:RetainedEarnings")
    assert p_re.credit == Decimal("1000.00")

    # Expense (debit-normal) closes by CREDITing expense and DEBITing retained earnings.
    p_rent = _find_posting(exp_entry, "Expenses:Rent")
    assert p_rent.credit == Decimal("400.00")
    p_re2 = _find_posting(exp_entry, "Equity:RetainedEarnings")
    assert p_re2.debit == Decimal("400.00")


def test_closing_entries_negative_balances_sign_safe() -> None:
    tb_adj = _tb(
        [
            # Abnormal debit balance in a revenue account -> close by CREDITing the revenue.
            {"account": "Revenue:Sales", "root": "Revenue", "balance": "-120.00"},
            # Abnormal credit balance in an expense account -> close by DEBITing the expense.
            {"account": "Expenses:Rent", "root": "Expenses", "balance": "-30.00"},
        ]
    )

    close = closing_entries_from_adjusted_tb(tb_adj, period="2026-01", close_date=date(2026, 1, 31))
    assert len(close) == 2

    rev_entry = close[0]
    exp_entry = close[1]

    p_sales = _find_posting(rev_entry, "Revenue:Sales")
    assert p_sales.credit == Decimal("120.00")
    p_re = _find_posting(rev_entry, "Equity:RetainedEarnings")
    assert p_re.debit == Decimal("120.00")

    p_rent = _find_posting(exp_entry, "Expenses:Rent")
    assert p_rent.debit == Decimal("30.00")
    p_re2 = _find_posting(exp_entry, "Equity:RetainedEarnings")
    assert p_re2.credit == Decimal("30.00")


def test_closing_entries_zero_safe() -> None:
    tb_adj = _tb(
        [
            {"account": "Revenue:Sales", "root": "Revenue", "balance": "0.00"},
            {"account": "Expenses:Rent", "root": "Expenses", "balance": "0.00"},
        ]
    )
    close = closing_entries_from_adjusted_tb(tb_adj, period="2026-01", close_date=date(2026, 1, 31))
    assert close == []


def test_closing_entries_dividends_close_to_retained_earnings() -> None:
    tb_adj = _tb(
        [
            # Equity root is credit-normal, so a debit-normal dividends account shows as negative.
            {"account": "Equity:Dividends", "root": "Equity", "balance": "-25.00"},
        ]
    )

    close = closing_entries_from_adjusted_tb(tb_adj, period="2026-01", close_date=date(2026, 1, 31))
    assert len(close) == 1
    e = close[0]

    p_div = _find_posting(e, "Equity:Dividends")
    assert p_div.credit == Decimal("25.00")
    p_re = _find_posting(e, "Equity:RetainedEarnings")
    assert p_re.debit == Decimal("25.00")
    assert all(p.account != "Equity:IncomeSummary" for p in e.postings)

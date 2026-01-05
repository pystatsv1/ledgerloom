"""Deterministic money helpers.

Chapters intentionally write monetary amounts as strings with 2 decimals.
Internally, the engine computes in integer cents to avoid floating-point drift.

Why integer cents?
- Avoids floating-point rounding drift.
- Makes invariants testable (sums are exact integers).
- Keeps output deterministic across platforms.

Why explicit rounding?
`Decimal.quantize` can consult the ambient Decimal context if no rounding mode is
specified. LedgerLoom makes rounding explicit so results are stable and the
convention is documented.

For v0.1, LedgerLoom uses ROUND_HALF_UP ("5 rounds up").
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")

# Rounding policy for converting arbitrary decimal amounts to integer cents.
#
# Accounting convention note:
# - ROUND_HALF_UP is common for currency rounding (ties go away from zero).
# - In later chapters (tax, payroll, etc.) you might introduce banker's rounding,
#   but v0.1 keeps the policy simple and explicit.
_MONEY_ROUNDING = ROUND_HALF_UP


def to_cents(x: Decimal) -> int:
    """Quantize to cents and return an integer number of cents."""

    q = x.quantize(_CENT, rounding=_MONEY_ROUNDING)
    return int(q * 100)


def str_to_cents(s: str) -> int:
    """Parse a decimal string and return integer cents.

    This is primarily used for internal view computation.

    Note: input is rounded to cents using the engine's rounding policy.
    """

    return to_cents(Decimal(s))


def cents_to_str(cents: int) -> str:
    """Format cents as a fixed 2-decimal string.

    Examples:
        0 -> "0.00"
        12 -> "0.12"
        -305 -> "-3.05"
    """

    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    dollars = cents // 100
    rem = cents % 100
    return f"{sign}{dollars}.{rem:02d}"

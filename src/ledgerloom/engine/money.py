"""Deterministic money helpers.

Chapters intentionally write monetary amounts as strings with 2 decimals.
Internally, the engine computes in integer cents to avoid floating-point drift.
"""

from __future__ import annotations

from decimal import Decimal

_CENT = Decimal("0.01")


def to_cents(x: Decimal) -> int:
    """Quantize to cents and return an integer number of cents."""

    q = x.quantize(_CENT)
    return int(q * 100)


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

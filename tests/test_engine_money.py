"""Unit tests for engine money helpers.

These are intentionally small, direct tests (not golden files).
"""

from __future__ import annotations

from decimal import Decimal

from ledgerloom.engine.money import cents_to_str, str_to_cents, to_cents


def test_to_cents_rounds_half_up() -> None:
    assert to_cents(Decimal("0.004")) == 0
    assert to_cents(Decimal("0.005")) == 1
    assert to_cents(Decimal("1.234")) == 123
    assert to_cents(Decimal("1.235")) == 124

    # Negative values: ties go away from zero under HALF_UP.
    assert to_cents(Decimal("-0.004")) == 0
    assert to_cents(Decimal("-0.005")) == -1


def test_str_to_cents_and_cents_to_str_round_trip() -> None:
    for s in ["0.00", "12.34", "-3.05", "999999.99"]:
        cents = str_to_cents(s)
        assert cents_to_str(cents) == s

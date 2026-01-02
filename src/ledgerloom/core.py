from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List


@dataclass(frozen=True)
class Posting:
    """One line in an entry: an amount posted to a specific account.

    Exactly one of debit/credit must be > 0 (paper-era UI).
    """
    account: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if (self.debit > 0) == (self.credit > 0):
            raise ValueError("Posting must have exactly one of debit or credit > 0")


@dataclass(frozen=True)
class Entry:
    """A balanced journal entry (append-only event)."""
    dt: date
    narration: str
    postings: List[Posting]
    meta: Dict[str, str] = field(default_factory=dict)

    def validate_balanced(self) -> None:
        total_debits = sum((p.debit for p in self.postings), Decimal("0"))
        total_credits = sum((p.credit for p in self.postings), Decimal("0"))
        if total_debits != total_credits:
            raise ValueError(f"Unbalanced entry: debits={total_debits}, credits={total_credits}")

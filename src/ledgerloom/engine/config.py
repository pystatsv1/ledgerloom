"""LedgerLoom Engine configuration.

The "engine" is the reusable core that chapters can build on.

v0.1 design constraints
- Small surface area (a handful of types/functions).
- Explicit accounting conventions (normal balances by root).
- Deterministic math (integer cents / stable string formatting).
- Engine is pure-compute; chapters own file I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class LedgerEngineConfig:
    """Configuration for :class:`~ledgerloom.engine.ledger.LedgerEngine`.

    Roots are the first segment of an account path, e.g. ``Assets:Cash`` -> ``Assets``.

    Normal-balance convention:
    - debit-normal: balances increase with debits (Assets, Expenses)
    - credit-normal: balances increase with credits (Liabilities, Equity, Revenue)

    The engine treats unknown roots as debit-normal for computation, but invariants will
    report them.
    """

    debit_normal_roots: FrozenSet[str] = field(default_factory=lambda: frozenset({"Assets", "Expenses"}))
    credit_normal_roots: FrozenSet[str] = field(default_factory=lambda: frozenset({"Liabilities", "Equity", "Revenue"}))

    # Metadata keys used by demo chapters (can be changed by apps).
    entry_id_key: str = "entry_id"
    department_key: str = "department"

    @property
    def recognized_roots(self) -> FrozenSet[str]:
        return frozenset(set(self.debit_normal_roots) | set(self.credit_normal_roots))

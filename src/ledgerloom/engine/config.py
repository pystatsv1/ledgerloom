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
from typing import FrozenSet, Literal


@dataclass(frozen=True)
class Dimension:
    """A configurable segment (dimension) materialized into the postings fact table.

    Dimensions are read from ``Entry.meta`` and written as separate string columns
    on the postings table (e.g., department, project, location).

    This stays intentionally simple in v0.1:
    - Entry-level metadata only (no posting-level overrides).
    - Deterministic: dimension columns appear in the configured order.
    """

    # Column name written to postings fact table (e.g., "department", "project").
    name: str
    # Key read from Entry.meta (e.g., "department", "project_code").
    key: str
    # Value used when the key is missing (default keeps current behavior).
    default: str = ""
    # Strict-mode validation can require this dimension later (engine is opt-in).
    required: bool = False


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

    # Optional multi-dimensional segmentation (cost center, project, location, etc.).
    # If None, defaults to a single 'department' dimension using department_key.
    dimensions: tuple[Dimension, ...] | None = None

    # Optional stricter validation (opt-in):
    # - enforce required dimensions (Dimension.required)
    # - enforce posting line rules (non-negative + exactly one of debit/credit > 0)
    # - enforce balanced entries and strict entry_id if configured
    strict_validation: bool = False

    # Entry ID policy:
    # - "strict": raise if entry_id is missing (recommended for real systems)
    # - "generated": synthesize a stable entry_id when missing (teaching / migration)
    entry_id_policy: Literal["strict", "generated"] = "strict"

    @property
    def effective_dimensions(self) -> tuple[Dimension, ...]:
        """Return configured dimension specs in deterministic order.

        If ``dimensions`` is None, fall back to a single department dimension
        using ``department_key`` (backward-compatible with earlier chapters/apps).
        """

        if self.dimensions is None:
            return (Dimension(name="department", key=self.department_key),)
        return self.dimensions

    @property
    def recognized_roots(self) -> FrozenSet[str]:
        return frozenset(set(self.debit_normal_roots) | set(self.credit_normal_roots))

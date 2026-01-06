"""Bookset scenarios (v1).

This module exists primarily to keep chapter-to-chapter imports clean.

As LedgerLoom grows, multiple chapters will want to reuse the same *accounting
scenario* steps (e.g., close a period, compute an opening entry, reconcile A/R
control accounts, etc.). Those steps are *business logic* and should live in a
public module, not as private helpers inside earlier chapters.

For now, we keep the surface area minimal and stable. Chapters 08–10+ can
converge on these functions over time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ledgerloom.core import Entry
from ledgerloom.engine import LedgerEngine, LedgerEngineConfig


@dataclass(frozen=True)
class PostCloseSnapshot:
    """Outputs commonly produced by a period-close routine."""

    postings_post_close: pd.DataFrame
    trial_balance_post_close: pd.DataFrame
    as_of: date


def compute_post_close_snapshot(*, cfg: LedgerEngineConfig) -> PostCloseSnapshot:
    """Compute a post-close snapshot for the bookset.

    Placeholder implementation.

    Chapters currently implement their own close logic (see Chapter 08). As we
    refactor, Chapter 08 will become the source-of-truth implementation here.
    """

    raise NotImplementedError(
        "compute_post_close_snapshot() is a scenarios stub. "
        "For now, use the Chapter 08 runner until the scenario is wired up."
    )


def compute_opening_from_post_close(
    *,
    tb_post_close: pd.DataFrame,
    opening_date: date,
    cfg: LedgerEngineConfig,
    entry_id: str = "OPENING",
) -> Entry:
    """Create an opening entry from a post-close trial balance.

    Placeholder implementation.

    Chapters 08.5/09 already demonstrate this concept. The long-term goal is to
    move that logic here and keep chapters focused on teaching + artifacts.
    """

    _ = (tb_post_close, opening_date, cfg, entry_id)
    raise NotImplementedError(
        "compute_opening_from_post_close() is a scenarios stub. "
        "For now, use the Chapter 08.5 runner until the scenario is wired up."
    )


def _engine(cfg: LedgerEngineConfig) -> LedgerEngine:
    """Internal convenience: build a LedgerEngine for scenario helpers."""

    return LedgerEngine(cfg=cfg)

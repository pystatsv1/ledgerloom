"""Reclass template generation.

This module is intentionally *pure* (no filesystem I/O). It transforms the
contents of ``unmapped.csv`` (rows posted to a suspense account) into a
copy/paste-friendly ``reclass_template.csv`` DataFrame that an accountant can
complete and use for manual reclassification.

Later PRs can wire this into ``ledgerloom check`` and ``ledgerloom build``.
"""

from __future__ import annotations

import pandas as pd

RECLASS_TEMPLATE_COLUMNS: list[str] = [
    "entry_id",
    "date",
    "description",
    "original_amount",
    "suspense_account",
    "reclass_account",
    "note",
]

_NOTE_TODO = "TODO: Verify and assign correct account"


def reclass_template_from_unmapped(unmapped: pd.DataFrame) -> pd.DataFrame:
    """Build a reclass template DataFrame from an ``unmapped.csv`` DataFrame.

    Required input columns (extra columns are ignored):
    - entry_id
    - date
    - original_description (preferred) OR description
    - original_amount (preferred) OR amount
    - suspense_account

    Output is deterministic:
    - stable column ordering (``RECLASS_TEMPLATE_COLUMNS``)
    - stable row ordering (sorted by entry_id, then date, then description)
    """
    if unmapped is None or len(unmapped) == 0:
        return pd.DataFrame(columns=RECLASS_TEMPLATE_COLUMNS)

    desc_col = (
        "original_description"
        if "original_description" in unmapped.columns
        else ("description" if "description" in unmapped.columns else None)
    )
    amt_col = (
        "original_amount"
        if "original_amount" in unmapped.columns
        else ("amount" if "amount" in unmapped.columns else None)
    )

    if desc_col is None:
        raise KeyError("Missing required column: original_description (or description)")
    if amt_col is None:
        raise KeyError("Missing required column: original_amount (or amount)")

    required = ["entry_id", "date", desc_col, amt_col, "suspense_account"]
    missing = [c for c in required if c not in unmapped.columns]
    if missing:
        raise KeyError(f"Missing required column(s): {', '.join(missing)}")

    out = pd.DataFrame(
        {
            "entry_id": unmapped["entry_id"].astype(str),
            "date": unmapped["date"].astype(str),
            "description": unmapped[desc_col].astype(str),
            "original_amount": unmapped[amt_col],
            "suspense_account": unmapped["suspense_account"].astype(str),
            "reclass_account": "",
            "note": _NOTE_TODO,
        }
    )

    # Stable ordering across platforms/runs.
    out = out.sort_values(
        by=["entry_id", "date", "description"],
        kind="mergesort",
    ).reset_index(drop=True)

    return out[RECLASS_TEMPLATE_COLUMNS]

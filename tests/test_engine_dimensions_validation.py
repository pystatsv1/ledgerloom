from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ledgerloom.core import Entry, Posting
from ledgerloom.engine import Dimension, LedgerEngine, LedgerEngineConfig


def test_postings_fact_table_materializes_configured_dimensions() -> None:
    cfg = LedgerEngineConfig(
        dimensions=(
            Dimension(name="department", key="dept"),
            Dimension(name="project", key="project", default="(none)"),
        )
    )
    eng = LedgerEngine(cfg)

    entries = [
        Entry(
            dt=date(2026, 1, 1),
            narration="Test",
            meta={"entry_id": "E0001", "dept": "HQ", "project": "ALPHA"},
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("10.00"), credit=Decimal("0.00")),
                Posting(account="Revenue:Sales", debit=Decimal("0.00"), credit=Decimal("10.00")),
            ],
        )
    ]
    postings = eng.postings_fact_table(entries)

    assert "department" in postings.columns
    assert "project" in postings.columns
    assert postings.loc[0, "department"] == "HQ"
    assert postings.loc[0, "project"] == "ALPHA"


def test_balances_by_dimension_groups_by_dimension_and_root() -> None:
    cfg = LedgerEngineConfig(
        dimensions=(
            Dimension(name="department", key="department"),
            Dimension(name="project", key="project"),
        )
    )
    eng = LedgerEngine(cfg)

    entries = [
        Entry(
            dt=date(2026, 1, 1),
            narration="Alpha cash sale",
            meta={"entry_id": "E0001", "department": "HQ", "project": "ALPHA"},
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("100.00"), credit=Decimal("0.00")),
                Posting(account="Revenue:Sales", debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        ),
        Entry(
            dt=date(2026, 1, 2),
            narration="Beta cash sale",
            meta={"entry_id": "E0002", "department": "HQ", "project": "BETA"},
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("50.00"), credit=Decimal("0.00")),
                Posting(account="Revenue:Sales", debit=Decimal("0.00"), credit=Decimal("50.00")),
            ],
        ),
    ]
    postings = eng.postings_fact_table(entries)

    by_project = eng.balances_by_dimension(postings, dimension="project")

    # For normal-balance convention: Assets positive, Revenue positive.
    alpha_assets = by_project[(by_project["project"] == "ALPHA") & (by_project["root"] == "Assets")].iloc[0]["balance"]
    alpha_rev = by_project[(by_project["project"] == "ALPHA") & (by_project["root"] == "Revenue")].iloc[0]["balance"]
    assert alpha_assets == "100.00"
    assert alpha_rev == "100.00"


def test_strict_validation_enforces_required_dimensions_and_posting_rules() -> None:
    cfg = LedgerEngineConfig(
        dimensions=(Dimension(name="project", key="project", required=True),),
        strict_validation=True,
    )
    eng = LedgerEngine(cfg)

    entries_missing_project = [
        Entry(
            dt=date(2026, 1, 1),
            narration="Missing project",
            meta={"entry_id": "E0001"},
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("10.00"), credit=Decimal("0.00")),
                Posting(account="Revenue:Sales", debit=Decimal("0.00"), credit=Decimal("10.00")),
            ],
        )
    ]
    with pytest.raises(ValueError, match="missing required dimension"):
        eng.postings_fact_table(entries_missing_project)

    # Negative amount sneaks past Posting.__post_init__ if the other side is positive.
    entries_negative_debit = [
        Entry(
            dt=date(2026, 1, 1),
            narration="Negative debit sneaks in",
            meta={"entry_id": "E0002", "project": "ALPHA"},
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("-10.00"), credit=Decimal("10.00")),
                Posting(account="Revenue:Sales", debit=Decimal("20.00"), credit=Decimal("0.00")),
            ],
        )
    ]
    with pytest.raises(ValueError, match="non-negative"):
        eng.postings_fact_table(entries_negative_debit)

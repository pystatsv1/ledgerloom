"""Unit tests for the engine's contract-level behavior.

These tests are designed to make engine refactors safer by asserting invariants
and helper behavior directly (separate from chapter golden files).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine, LedgerEngineConfig


def _sample_entries() -> list[Entry]:
    return [
        Entry(
            dt=date(2026, 1, 1),
            narration="Owner contribution",
            postings=[
                Posting(account="Assets:Cash", debit=Decimal("100.00")),
                Posting(account="Equity:OwnerCapital", credit=Decimal("100.00")),
            ],
            meta={"entry_id": "E0001", "department": "HQ"},
        ),
        Entry(
            dt=date(2026, 1, 15),
            narration="Office supplies",
            postings=[
                Posting(account="Expenses:Supplies", debit=Decimal("25.00")),
                Posting(account="Assets:Cash", credit=Decimal("25.00")),
            ],
            meta={"entry_id": "E0002", "department": "HQ"},
        ),
    ]


def test_postings_as_of_filters_by_date() -> None:
    cfg = LedgerEngineConfig()
    eng = LedgerEngine(cfg)
    entries = _sample_entries()
    postings = eng.postings_fact_table(entries)

    as_of_early = eng.postings_as_of(postings, as_of="2026-01-01")
    assert as_of_early["entry_id"].unique().tolist() == ["E0001"]

    as_of_late = eng.postings_as_of(postings, as_of=date(2026, 1, 31))
    assert set(as_of_late["entry_id"].unique().tolist()) == {"E0001", "E0002"}


def test_invariants_include_contract_checks_and_pass_for_well_formed_input() -> None:
    cfg = LedgerEngineConfig()
    eng = LedgerEngine(cfg)
    entries = _sample_entries()
    postings = eng.postings_fact_table(entries)

    inv = eng.invariants(entries, postings)

    # Existing invariants.
    assert inv["entry_double_entry_ok"] is True
    assert inv["ledger_raw_delta_zero"] is True
    assert inv["posting_id_unique"] is True

    # Contract-level checks (added for engine hardening).
    assert inv["entry_id_present"] is True
    assert inv["entry_id_unique"] is True
    assert inv["date_format_ok"] is True
    assert inv["posting_id_format_ok"] is True
    assert inv["posting_id_entry_id_ok"] is True
    assert inv["posting_id_line_no_ok"] is True
    assert inv["missing_entry_ids"] == []
    assert inv["bad_posting_ids"] == []
    assert inv["bad_dates"] == []

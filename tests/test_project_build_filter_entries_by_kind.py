from __future__ import annotations

from datetime import date
from decimal import Decimal

from ledgerloom.core import Entry, Posting
from ledgerloom.project.build import _filter_entries_by_kind


def _mk_entry(*, entry_id: str, entry_kind: str | None) -> Entry:
    meta: dict[str, str] = {"entry_id": entry_id}
    if entry_kind is not None:
        meta["entry_kind"] = entry_kind

    return Entry(
        dt=date(2026, 1, 1),
        narration=entry_id,
        postings=[
            Posting(account="Assets:Cash", debit=Decimal("1"), credit=Decimal("0")),
            Posting(account="Revenue:Sales", debit=Decimal("0"), credit=Decimal("1")),
        ],
        meta=meta,
    )


def test_filter_entries_by_kind_none_means_no_filter() -> None:
    entries = [
        _mk_entry(entry_id="t1", entry_kind=None),
        _mk_entry(entry_id="a1", entry_kind="adjustment"),
        _mk_entry(entry_id="c1", entry_kind="closing"),
    ]

    assert _filter_entries_by_kind(entries=entries, allowed_kinds=None) == entries


def test_filter_entries_by_kind_filters_and_defaults_to_transaction() -> None:
    e_default = _mk_entry(entry_id="t1", entry_kind=None)
    e_blank = _mk_entry(entry_id="t2", entry_kind="")
    e_adj = _mk_entry(entry_id="a1", entry_kind="adjustment")
    e_close = _mk_entry(entry_id="c1", entry_kind="closing")
    entries = [e_default, e_blank, e_adj, e_close]

    assert _filter_entries_by_kind(entries=entries, allowed_kinds={"transaction"}) == [
        e_default,
        e_blank,
    ]
    assert _filter_entries_by_kind(entries=entries, allowed_kinds={"adjustment", "closing"}) == [
        e_adj,
        e_close,
    ]


def test_filter_entries_by_kind_case_insensitive() -> None:
    e_adj = _mk_entry(entry_id="a1", entry_kind="Adjustment")
    e_txn = _mk_entry(entry_id="t1", entry_kind=None)

    assert _filter_entries_by_kind(entries=[e_adj, e_txn], allowed_kinds={"adjustment"}) == [
        e_adj
    ]


def test_filter_entries_by_kind_empty_set_means_none_allowed() -> None:
    entries = [_mk_entry(entry_id="t1", entry_kind=None)]
    assert _filter_entries_by_kind(entries=entries, allowed_kinds=set()) == []

Engine Data Model Reference
===========================

This appendix is the **single source of truth** for LedgerLoom’s engine data model.
It defines the tables, columns, and invariants produced by the engine.

If you only read one technical document in LedgerLoom, make it this one.

Vocabulary
----------

Entry
  A journal entry: dated narration + a set of postings that must balance.

Posting
  One line of an entry: an account and either a debit or credit amount.

Postings fact table
  A normalized table with one row per posting line. This is the engine’s
  canonical database representation.

Roots
  The left-most segment of an account string (e.g., ``Assets`` in
  ``Assets:Cash``). Roots are used for rollups and conventions.

Segments
  Optional attributes (e.g., ``department``) stored on an entry and copied down
  to postings so you can group/slice balances.

Stable IDs
----------

``entry_id``
  A stable identifier pulled from ``entry.meta[entry_id_key]``.

``posting_id``
  A stable identifier for a posting line, of the form ``{entry_id}:{line_no}``.

These IDs are not just convenience:

- They make debugging faster (you can trace a number back to a source line).
- They enable deterministic tests.
- They support reproducible ETL / analytics workflows.

Postings fact table
-------------------

The engine function :func:`ledgerloom.engine.ledger.postings_fact_table` returns
a DataFrame with one row per posting.

Columns
~~~~~~~

``posting_id``
  Stable posting identifier.

``entry_id``
  Stable entry identifier (copied to every posting of that entry).

``line_no``
  Posting line number within the entry (01, 02, ...).

``date``
  Entry date as ISO string (YYYY-MM-DD).

``period``
  Accounting period as ISO month (YYYY-MM). Derived from ``date``.

``narration``
  Entry narration (human context).

``account``
  Colon-delimited account path (e.g., ``Assets:Cash``).

``root``
  Root segment of the account path (e.g., ``Assets``).

``debit`` / ``credit``
  Monetary amounts as **strings with 2 decimals** (e.g., ``"12.34"``).

``raw_delta``
  ``debit - credit`` as a string with 2 decimals.

``signed_delta``
  A sign-normalized delta using a root convention:

  - Assets, Expenses: debit-normal (+ = increase)
  - Liabilities, Equity, Revenue: credit-normal (+ = increase)

``department``
  Example segment copied from entry metadata (if present).

Derived views
-------------

The engine provides a few small, reusable views derived from the fact table.
Think of these as "materialized queries" that chapters and users can reuse.

:func:`ledgerloom.engine.ledger.balances_by_account`
  Group postings by account and compute totals.

:func:`ledgerloom.engine.ledger.balances_by_period`
  Group postings by period and compute totals.

:func:`ledgerloom.engine.ledger.balances_by_department`
  Group postings by department and compute totals.

:func:`ledgerloom.engine.ledger.running_balance_by_posting`
  Stable running balance (ordered by date, entry_id, line_no).

As-of filtering
---------------

Many real-world questions are "as of" a point in time:

- Balance sheet **as of** 2026-01-31
- Revenue **as of** month-end

The helper :func:`ledgerloom.engine.ledger.postings_as_of` filters postings to
``date <= as_of`` and is designed to be safe and deterministic when dates are in
ISO format.

Invariants
----------

The engine computes invariants with :func:`ledgerloom.engine.ledger.invariants`.
These are **constraints** you can assert in unit tests, CI, or validation steps.

Core invariants
~~~~~~~~~~~~~~~

``entry_double_entry_ok``
  Every entry has debits == credits.

``ledger_raw_delta_zero``
  The total of ``raw_delta`` across all postings equals zero.

``posting_id_unique``
  Posting IDs are unique.

Schema hygiene
~~~~~~~~~~~~~~

``unknown_roots``
  Roots not in the engine’s recognized set.

Contract checks
~~~~~~~~~~~~~~~

These checks make refactors safer and debugging faster:

- ``entry_id_present`` and ``entry_id_unique``
- ``date_format_ok`` (YYYY-MM-DD)
- ``posting_id_format_ok`` (``{entry_id}:{NN}``)
- ``posting_id_entry_id_ok`` and ``posting_id_line_no_ok``

When a check fails, the invariants dictionary includes small diagnostic lists
(e.g., ``bad_posting_ids``).

Why this model works for all three audiences
--------------------------------------------

Accountants
  You can interpret postings as a journal expanded into a ledger and trust the
  constraints.

Developers
  You can treat the ledger as a pure function: inputs → facts → views,
  with invariants as tests.

Data professionals
  You can treat postings as a fact table and build analytics with groupbys or SQL.

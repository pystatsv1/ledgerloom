Appendix: Data model reference
==============================

This appendix describes the **canonical tables** produced by the LedgerLoom engine.
It is written as a *contract*: if these structures are stable, chapter refactors and
new report views remain safe.

Stable identifiers
------------------

LedgerLoom uses stable identifiers so every number in a statement can be traced
back to an exact event.

Entry IDs (``entry_id``)
^^^^^^^^^^^^^^^^^^^^^^^^

Each :class:`ledgerloom.core.Entry` should have a stable ID stored in
``entry.meta[cfg.entry_id_key]`` (default key: ``"entry_id"``).

Two policies exist (see :class:`ledgerloom.engine.config.LedgerEngineConfig`):

- **Strict (default):** missing ``entry_id`` raises immediately. This mirrors real systems
  where matching (A/R open items, A/P matching, reconciliations) depends on durable keys.
- **Generated (optional):** ``entry_id_policy="generated"`` synthesizes a stable ID
  (currently ``H<12 hex>``) from the entry's date, narration, and postings.

When the generated policy is enabled, :meth:`ledgerloom.engine.ledger.LedgerEngine.invariants`
adds a ``generated_entry_ids`` list so the run explicitly records what was synthesized.

Posting IDs (``posting_id``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each posting line is uniquely identified as::

  posting_id = "<entry_id>:<line_no>"

where ``line_no`` is formatted as two digits (01, 02, ...). The table also includes
``line_no`` as an integer column.

Postings fact table (``postings.csv``)
--------------------------------------

The engine compiles a list of entries into a single **fact table**: one row per posting line.
This is the "append-only truth" you build reports from.

Columns
^^^^^^^

- ``posting_id`` — stable line identifier (``<entry_id>:<line_no two digits>``)
- ``entry_id`` — stable entry identifier
- ``line_no`` — posting line number within the entry (1, 2, ...)
- ``date`` — ISO date string (``YYYY-MM-DD``)
- ``department`` — optional segment (example dimension used in early chapters)
- ``narration`` — human description of the event
- ``account`` — full account path (e.g., ``Assets:Cash``)
- ``root`` — first account segment (e.g., ``Assets``)
- ``debit`` — decimal string, two places
- ``credit`` — decimal string, two places
- ``raw_delta`` — ``debit - credit`` as a signed decimal string
- ``signed_delta`` — raw delta mapped into a "normal-balance" convention by root

Notes
^^^^^

- The engine is intentionally **not** a database. It produces database-shaped tables
  that you can load into Pandas/SQL/BI tools.
- **Period** is not stored in the fact table. Views (below) derive ``period`` by slicing
  the ``date`` field.

Derived views
-------------

The engine provides common "views" (materialized as DataFrames in chapters) derived from postings.

Balances by account (``balances_by_account.csv``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Groups postings by ``(root, account)`` and sums ``signed_delta``.

Balances by period (``balances_by_period.csv``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adds a derived ``period`` key (``YYYY-MM``) from ``date``, then groups by
``(period, root, account)``.

Balances by department (``balances_by_department.csv``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a ``department`` column exists, this view groups by ``(department, root, account)``.
(Other segment dimensions will appear in later chapters.)

As-of filtering
---------------

For point-in-time reporting (e.g., "balance as of 2026-01-31"), the engine provides
:meth:`ledgerloom.engine.ledger.LedgerEngine.postings_as_of`.

The contract is:

- include postings where ``date <= as_of``
- preserve stable ordering

Invariants (``invariants.json``)
--------------------------------

Invariants are explicit checks you can treat as unit tests.
Core invariants include:

- ``entry_double_entry_ok`` — every entry balances (debits == credits)
- ``ledger_raw_delta_zero`` — total ``raw_delta`` sums to 0 across the full ledger
- ``posting_id_unique`` — stable IDs are unique
- ``entry_id_present`` and ``entry_id_unique`` — entry IDs exist and are unique
- ``posting_id_format_ok`` — ``posting_id`` matches ``<entry_id>:<two digits>``

When ``entry_id_policy="generated"``, additional diagnostics are included:

- ``entry_id_policy`` — the active policy (currently ``"generated"``)
- ``generated_entry_ids`` — which entries required synthesized IDs and why

Why this appendix matters
-------------------------

If you are extending LedgerLoom, treat this appendix like a schema contract:

- New chapters should prefer **new derived views** over changing the fact table.
- Engine refactors should preserve these table shapes unless a version bump and doc update
  are intentional.

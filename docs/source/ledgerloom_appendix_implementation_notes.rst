Appendix: Implementation notes
==============================

This appendix collects “how the sausage is made” notes for LedgerLoom:

design decisions, determinism, and a quick tour of the engine.

LedgerLoom Engine v0.1
----------------------

As of ``v0.1.4``, LedgerLoom includes a small reusable core under:

``src/ledgerloom/engine/``

The goal is to keep the chapters readable while extracting the reusable mechanics:

- Chart of Accounts (COA) schema + validation
- Turning journal entries into a postings fact table
- Derived views (balances by account / period / segment)
- Invariant checks (the double-entry constraint, etc.)

The engine is intentionally **not** a database. Instead, it produces
“database-shaped” tables (CSV/JSON artifacts) that are easy to inspect, diff,
and load into real systems. The engine itself does not perform file I/O;
chapter runners handle writing artifacts.

Public surface area
^^^^^^^^^^^^^^^^^^^

These are the main objects intended to stay stable as the book grows:

- ``Money`` (``engine/money.py``): currency + integer cents (safe arithmetic)
- ``ChartOfAccounts`` (``engine/coa.py``): accounts + rollups + segment dimensions
- ``Posting`` and ``JournalEntry`` (``engine/ledger.py``): canonical “ledger events”
- ``LedgerEngine`` (``engine/ledger.py``): compiles + materializes common views

At a high level, Chapter runners do:

1. Build (or load) a COA
2. Generate a small set of ``JournalEntry`` objects
3. Compile them into a postings fact table
4. Materialize one or more views and write artifacts

Determinism
-----------

LedgerLoom treats each chapter as a deterministic pipeline:

- A ``--seed`` flag controls any synthetic data generation
- Postings are sorted stably by ``(date, entry_id, line_no)``
- Views are sorted by their grouping keys
- ``manifest.json`` records ``sha256`` for each artifact (reproducibility)

The tests prefer “shape and invariants” checks where possible, and golden files
only when the output is meant to be a fixed reference.

Chapter boundaries
------------------

Rule of thumb for where code should live:

- If it’s **accounting mechanics** you’ll reuse across chapters (posting compilation,
  rollups, balance aggregation, invariants), it belongs in ``ledgerloom.engine``.
- If it’s **narrative** (data generation, exposition, and chapter-specific outputs),
  keep it in the chapter runner.

This keeps the engine small and teachable, while allowing the “book” to remain
clear and focused.

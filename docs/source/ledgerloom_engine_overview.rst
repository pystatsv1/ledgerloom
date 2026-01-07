LedgerLoom Engine Overview
==========================

LedgerLoom’s **engine** is the project’s "accounting kernel": a small, testable
core that turns human-friendly journal entries into **canonical ledger tables**.

If you’re:

- an **accountant**, the engine is what makes results *trustworthy* (balanced,
  traceable, reproducible).
- a **software developer**, the engine is what makes the system *maintainable*
  (clear interfaces, pure compute, deterministic outputs).
- a **data professional**, the engine is what makes the ledger *queryable*
  (fact table + derived views).

What the engine does
--------------------

Given a list of :class:`ledgerloom.core.Entry` objects, the engine produces:

1. **Postings fact table** (one row per posting line)
2. A small set of **derived views** (balances by account, period, segment)
3. A dictionary of **invariants** (constraints you can assert in tests)

This mirrors how modern systems are built:

- **event log** (entries) as the append-only truth
- **facts** (postings) as the normalized database table
- **views** (balances/statements) as derived, reproducible computations
- **constraints** (invariants) as continuously checked correctness rules

Why an engine matters (software + accounting)
---------------------------------------------

Accounting is fundamentally about *consistency*:

- Every entry must balance (double-entry)
- The ledger must be internally coherent
- Reports must be derivable from recorded facts

Software engineering is fundamentally about *reliability over time*:

- small stable APIs
- separation of concerns
- deterministic builds and tests
- refactors that don’t change meaning

LedgerLoom’s engine is where these meet.
Chapters can focus on teaching and artifact writing, while the engine provides a
single source of truth for ledger math.

Where to go next
----------------

- :doc:`ledgerloom_engine_design_principles` — the software engineering ideas
  that make accounting systems safer.
- :doc:`ledgerloom_appendix_data_model_reference` — the authoritative reference
  for engine tables, columns, and invariants.
- :doc:`ledgerloom_engine_api_reference` — API docs for contributors.

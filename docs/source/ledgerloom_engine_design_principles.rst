Engine Design Principles
========================

LedgerLoom is a teaching project, but it is also designed to be *real*:
what you learn here should transfer to production accounting systems.

This page explains the **software engineering principles** behind the engine,
and how they reduce errors in practical accounting workflows.

Principle 1 — Separate compute from I/O
---------------------------------------

The engine lives under ``ledgerloom/engine`` and aims to be **pure compute**:

- It accepts in-memory objects (Entries) and returns in-memory tables (DataFrames).
- It does not write files.
- It does not rely on global state.

Chapters still need I/O (CSV/JSON outputs). LedgerLoom keeps that I/O outside the engine
*but* centralizes the **deterministic writing contract** in :mod:`ledgerloom.artifacts`
(stable column order, LF newlines, sorted JSON keys, sha256 manifests).


Why it matters:

- **Refactor-friendly:** you can change chapter artifact formats without breaking ledger math.
- **Testable:** you can unit-test accounting invariants without touching the filesystem.
- **Reusable:** the same engine can power CLIs, notebooks, web APIs, or batch jobs.

Principle 2 — Determinism by default
------------------------------------

Accounting systems must be auditable. That implies **reproducibility**:

- the same input entries should produce the same postings
- ordering should be stable
- rounding rules should be explicit

LedgerLoom encodes that as:

- integer-cent arithmetic (no floating-point drift)
- stable identifiers (``entry_id`` and ``posting_id``)
- stable sorts (``kind="mergesort"``)

By default, the engine is **strict**: entries must provide an ``entry_id`` in
``entry.meta``. For quick demos or exploratory notebooks, you can opt into
``entry_id_policy="generated"``, which synthesizes a stable hash-based ID; when enabled,
engine invariants include a ``generated_entry_ids`` list so the run remains auditable.

Principle 3 — Make invariants first-class
-----------------------------------------

In accounting, *constraints are the product*:

- an entry that doesn’t balance is not “mostly correct” — it is **invalid**
- a ledger that doesn’t sum correctly is **untrustworthy**

In LedgerLoom, invariants are computed explicitly (see the data model reference):

- ``entry_double_entry_ok`` — every entry debits equal credits
- ``ledger_raw_delta_zero`` — total (debit-credit) sums to zero across the ledger
- ``posting_id_unique`` — traceability depends on stable IDs
- ``unknown_roots`` — schema hygiene (COA consistency)

This is a deliberate software design move:

- invariants become unit tests
- unit tests become regression protection
- regression protection makes refactors safe

Principle 4 — Prefer fact tables + views
----------------------------------------

Data professionals recognize this pattern immediately:

- **Fact table:** postings (one row per posting line)
- **Dimensions:** account, root, department, period
- **Views:** balances and reports computed from facts

This has two advantages:

- It matches how BI / analytics pipelines work (SQL, star schemas, OLAP).
- It prevents “report drift” because statements are derived from the same facts.

Principle 5 — Minimal public surface area
-----------------------------------------

The engine intentionally keeps a small API (``LedgerEngine`` and a few helpers).

As the chapter count grows, cross-chapter reusable transformations should live in
:mod:`ledgerloom.scenarios` (a small, stable layer that prevents chapters from importing
private helpers from earlier chapters).
A small API is easier to:

- document
- test
- keep stable while the project grows to many chapters

As LedgerLoom grows, we prefer adding *new* helpers instead of changing
existing behavior, so old chapters remain correct.

How this makes accounting better in practice
--------------------------------------------

Putting these principles together leads to practical wins:

- **Fewer errors:** invariants catch imbalances immediately.
- **Faster debugging:** stable IDs make it easy to trace a report number back
  to the exact entry and posting line.
- **Better collaboration:** accountants and developers can talk about the same
  data model (facts + views + constraints).
- **Safer change management:** determinism + tests allow incremental refactors
  without fear of silently changing financial meaning.

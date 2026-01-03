LedgerLoom vision and roadmap
=============================

LedgerLoom teaches accounting using modern developer mental models: event logs, derived views,
invariants, and reproducible pipelines.

This page is the high-level roadmap. The full vision document lives in the repository as ``VISION.md``.

Core idea
---------

Don’t just calculate results — engineer them.

Near-term plan (MVP textbook arc)
---------------------------------

- Ch01: Journal vs event log (done)
- Ch02: Chart of accounts as schema
- Ch03: Debits/credits as sign convention + trial balance
- Ch04: Close process as deterministic transformation
- Ch05: Statements as projections (views)

How to contribute
-----------------

Contributions are easiest when they follow the chapter pattern:

- docs page (RST)
- deterministic script (seeded)
- tests for outputs
- Makefile target

See ``CONTRIBUTING.md`` for details.

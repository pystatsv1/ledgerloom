Chapter 01 — Journal vs Event Log
================================

This chapter bridges a traditional accounting **journal** with a developer-friendly **event log**.

- **Journal**: a table of debits/credits (what accountants record)
- **Event log**: an append-only stream of domain events (what software systems record)
- **Ledger view**: a *derived view* (projection) built deterministically from the event log
- **Trial balance**: an invariant check (debits == credits)

Run it
------

From the repo root (editable install) you can run:

.. code-block:: bash

   python -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir outputs/ledgerloom --seed 123

Or, if you are developing locally:

.. code-block:: bash

   make ll-ch01

Outputs
-------

The runner writes:

- ``journal.csv`` — the accounting journal
- ``eventlog.jsonl`` — the append-only event log (JSON Lines)
- ``ledger_view.csv`` — a derived ledger view (projection)
- ``trial_balance.csv`` — invariant check output
- ``entry_explanations.md`` — short human-readable notes

Why it matters
--------------

Accounting is a specification: if you store *events* and derive *views*, you can reproduce
the books exactly, test invariants, and explain transformations step-by-step.
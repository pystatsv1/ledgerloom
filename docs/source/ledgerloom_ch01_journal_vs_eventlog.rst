Chapter 01 — Journal vs Event Log
================================

This chapter reframes the "journal" as an **append-only event log**, then shows how familiar
accounting outputs (ledger, trial balance, statements) are just **deterministic views** over
those immutable facts.

Developer mapping
-----------------

* **Journal entry** → event (immutable fact)
* **Journal (table)** → one possible *view* of those events
* **General ledger** → derived view (projection / materialized view)
* **Double-entry** → invariant (sum(debits) == sum(credits) per entry)
* **Trial balance** → automated check over account totals

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

The runner writes a small set of artifacts under ``outputs/ledgerloom/ch01/``:

Core artifacts
^^^^^^^^^^^^^

* ``eventlog.jsonl`` — append-only event log (JSON Lines)
* ``journal.csv`` — traditional journal view (one row per posting with debit/credit columns)
* ``ledger_view.csv`` — derived ledger view with running balances by account

Checks and statements
^^^^^^^^^^^^^^^^^^^^^

* ``trial_balance.csv`` — account totals (derived check)
* ``income_statement.csv`` — income statement from the trial balance
* ``balance_sheet.csv`` — balance sheet (includes a ``Check`` value that should be 0)

Explainability + reproducibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``entry_explanations.md`` — human-friendly explanation of each entry
* ``run_meta.json`` — artifact hashes + counts for reproducible runs
* ``summary.md`` — short memo describing what was generated

Why it matters
--------------

If you store *events* and derive *views*, you can:

* reproduce outputs exactly (deterministic pipeline)
* validate invariants continuously (tests, CI)
* explain transformations step-by-step (audit-friendly artifacts)

This is the foundation for the rest of LedgerLoom: later chapters add richer business events,
schema validation, and period-end workflows — but the mental model stays the same.
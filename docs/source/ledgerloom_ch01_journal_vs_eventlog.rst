Chapter 01 — Journal vs Event Log
=================================

This chapter gives you the core LedgerLoom mental model in one runnable, inspectable demo:

* **Store immutable facts** (an append-only *event log*)
* **Derive views + reports** (journal, ledger view, trial balance, statements)
* **Enforce invariants** (double-entry, accounting equation check)
* **Ship reproducible artifacts** (manifests, checksums, memos)

If you already think in terms of databases, data pipelines, and tests, this will feel familiar.


What you will build
-------------------

Running the Chapter 01 CLI produces a tiny, deterministic dataset and writes a small “artifact bundle”
under ``outputs/ledgerloom/ch01/``:

* an **event log** (JSONL)
* a **journal view** (CSV)
* a **ledger view** (CSV with running balances)
* a **trial balance** (CSV check/view)
* an **income statement** and **balance sheet** (CSV)
* a handful of **WOW artifacts** for explainability and reproducibility:

  * ``tables.md`` (tables rendered as Markdown)
  * ``checks.md`` (human-readable invariant results)
  * ``lineage.mmd`` (a pipeline diagram)
  * ``manifest.json`` (what was produced + hashes)


Developer mapping
-----------------

LedgerLoom intentionally translates accounting terms into developer mental models:

=====================  ==============================================
Accounting concept      Developer mental model
=====================  ==============================================
Journal entry           Event (immutable fact)
Journal (table)         One possible view of the events
General ledger          Derived view / projection / materialized view
Double-entry            Invariant: ``sum(debits) == sum(credits)``
Trial balance           Automated check over account totals
Financial statements    Deterministic report views over a validated TB
Audit trail             Reproducible artifacts + lineage + diffs
=====================  ==============================================


Run it
------

From the repo root (editable install):

.. code-block:: bash

   python -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir outputs/ledgerloom --seed 123

Or use the Makefile target:

.. code-block:: bash

   make ll-ch01

You should see something like:

.. code-block:: text

   Wrote LedgerLoom Chapter 01 artifacts -> outputs/ledgerloom/ch01


Open the outputs
----------------

Go to ``outputs/ledgerloom/ch01/`` and scan these first:

* ``summary.md`` — the “what happened” memo
* ``tables.md`` — journal + trial balance + statements as Markdown
* ``checks.md`` — invariant results (so you can eyeball PASS/FAIL)
* ``manifest.json`` — artifact list + hashes (reproducibility)


Core artifacts
--------------

The chapter produces multiple representations of the same underlying facts.


1) Event log (canonical truth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The event log is the canonical record:

* ``ledger.jsonl`` — canonical name
* ``eventlog.jsonl`` — friendly alias used in the README/VISION

Each line is a JSON object representing **one balanced entry**.
Here’s what a single line *conceptually* looks like (formatting added for readability):

.. code-block:: json

   {
     "dt": "2026-01-02",
     "meta": {"doc": "INV-0001"},
     "narration": "Invoice client for services",
     "postings": [
       {"account": "Assets:AccountsReceivable", "credit": "0", "debit": "1000.00"},
       {"account": "Revenue:Services", "credit": "1000.00", "debit": "0"}
     ]
   }

Why JSONL?

* append-only
* diff-friendly
* easy to stream
* easy to validate

The **journal table**, **ledger view**, and **reports** are derived from this immutable log.


2) Journal view (classic accounting table)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``journal.csv`` is a traditional journal view:

* one row per posting
* explicit debit/credit columns
* includes ``entry_id`` and ``line_no`` for readability

This is a *view* of the event log, not a separate source of truth.


3) Ledger view (developer-friendly derived view)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ledger_view.csv`` is a derived projection that feels like a “database view”:

* per-posting deltas
* per-account running balances
* type-aware sign convention (assets/expenses increase on debits; income/liab/equity increase on credits)

This is where developers often “get it”: the general ledger is a **materialized view**.


Checks and reports
------------------


Double-entry invariant
^^^^^^^^^^^^^^^^^^^^^^

LedgerLoom treats double-entry as a testable constraint:

* each entry must satisfy: ``sum(debits) == sum(credits)``

You can see this in two places:

* code-level validation (entries validate as balanced)
* artifact-level proof:

  * ``entry_balancing.csv`` — debits/credits totals per entry
  * ``checks.md`` — PASS/FAIL summary


Trial balance
^^^^^^^^^^^^^

``trial_balance.csv`` is an automated check/view:

* it aggregates balances by account
* it only exists because the event log is valid


Statements
^^^^^^^^^^

The statements are deterministic summaries over the trial balance:

* ``income_statement.csv``
* ``balance_sheet.csv`` (includes a ``Check`` row)

In this early chapter, the balance sheet includes a *computed* close effect:

* Net income is treated as an increase to equity (``EquityAfterClose``)
* The accounting equation check is:

  ``Assets - (Liabilities + EquityAfterClose) == 0``

If the ``Check`` row is non-zero, something is wrong.


“Wow” factor artifacts
----------------------

LedgerLoom isn’t just about computing numbers — it’s about engineering trust.
So Chapter 01 produces several “audit-friendly” artifacts:

* ``entry_explanations.md`` — narrative explanation of each entry
* ``assumptions.md`` — scope + what is intentionally not modeled yet
* ``tables.md`` — key tables rendered as Markdown for fast inspection
* ``root_bar_chart.md`` — a tiny visual sanity check (bars by account root)
* ``lineage.mmd`` — a diagram of the pipeline (events → views → reports)
* ``run_meta.json`` — hashes + sizes of artifacts (reproducible builds)
* ``manifest.json`` — human-friendly artifact catalog

These are designed to be useful in:

* PR reviews
* debugging
* teaching
* “audit trail” conversations


Try a modification (exercise)
-----------------------------

Open the chapter runner:

``src/ledgerloom/chapters/ch01_journal_vs_eventlog.py``

Add a new entry to the demo, for example:

* owner invests cash (Assets:Cash up; Equity:OwnerCapital up)

Then re-run:

.. code-block:: bash

   make lint
   pytest -q
   make ll-ch01

If you added an unbalanced entry, one of the checks will fail (and that’s the point).


Next
----

Chapter 02 explains the “debit/credit” system as an **encoding choice** and introduces a modern
signed representation.

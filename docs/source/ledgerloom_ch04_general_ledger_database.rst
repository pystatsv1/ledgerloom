Chapter 04: General Ledger as a database
========================================

Status: **WOW (early adopter pass)**

This chapter treats a *general ledger* like what it really is for developers:

- an **append-only fact table** (postings)
- a few **dimension tables** (accounts, segments)
- a set of **derived views** (balances) built with grouping + aggregation
- a set of **constraints** that keep everything true (double-entry invariants)

If you can think in SQL, you can think in ledgers.

What you will build
-------------------

You will run a deterministic chapter runner that writes a small “mini-database”
worth of artifacts under ``outputs/ledgerloom/ch04``:

- ``postings.csv`` — the **fact table** (one row per posting)
- ``balances_by_account.csv`` — a **materialized view** (group by account)
- ``balances_by_period.csv`` — group by period + root + account
- ``balances_by_department.csv`` — group by segment (department) + root
- ``running_balance_by_posting.csv`` — window function: running balance per account
- ``invariants.json`` — constraint checks (double-entry + basic DB rules)
- ``gl_schema.json`` — table schemas + index suggestions
- ``sql_mental_model.md`` — “developer translation” (pandas ↔ SQL)
- ``manifest.json`` — SHA-256 file digests for reproducibility
- ``lineage.mmd`` — a small DAG of how artifacts are derived
- ``run_meta.json`` — seed + environment info (reproducibility)

Why this is “database thinking”
-------------------------------

A database mindset is a superpower for accounting systems:

- **Fact table**: a posting is the atomic event you query.
- **Constraints**: each entry must balance (sum debits == sum credits).
- **Derived views**: everything you *report* is computed from postings.
- **Immutability**: treat postings as append-only; rebuild views as needed.

The runner in this chapter builds these ideas explicitly and writes out both the
raw table and the views.

SQL mental model
----------------

The artifacts are produced using grouping/aggregation patterns that map
directly to SQL.

Example: balances by account

.. code-block:: sql

   SELECT
     account,
     SUM(debit_cents)  AS debit_cents,
     SUM(credit_cents) AS credit_cents
   FROM postings
   GROUP BY account
   ORDER BY account;

In the runner we do the same operation with pandas groupby, then write the view
to ``balances_by_account.csv``.

Example: balances by period + root + account

.. code-block:: sql

   SELECT
     period,
     root,
     account,
     SUM(signed_delta_cents) AS balance_cents
   FROM postings
   GROUP BY period, root, account
   ORDER BY period, root, account;

Example: running balance (window function)

.. code-block:: sql

   SELECT
     *,
     SUM(signed_delta_cents) OVER (
       PARTITION BY account
       ORDER BY date, entry_id, line_no
     ) AS running_balance_cents
   FROM postings
   ORDER BY date, entry_id, line_no;

This view is written to ``running_balance_by_posting.csv``.

How to run
----------

From the project root:

.. code-block:: bash

   # Run the chapter runner (deterministic seed)
   make ll-ch04

Or call the module directly:

.. code-block:: bash

   python -m ledgerloom.chapters.ch04_general_ledger_database \
     --outdir outputs/ledgerloom \
     --seed 123

You should see:

- ``Wrote LedgerLoom Chapter 04 artifacts -> outputs/ledgerloom/ch04``

Invariant checks you can trust
------------------------------

This chapter generates ``invariants.json`` that validates:

- **Double-entry**: every entry balances (debits == credits)
- **Ledger-wide balance**: total (debit - credit) is exactly zero
- **Primary key uniqueness**: posting_id is unique
- **Allowed roots**: account roots are one of Assets/Liabilities/Equity/Revenue/Expenses

The checks are designed to fail loudly if anything drifts.

Contributor notes
-----------------

- All CSV outputs are forced to **LF (\n)** line endings to keep golden-file tests
  stable across Windows/macOS/Linux.
- Golden tests compare bytes (not “parsed” tables) on purpose — the goal is
  reproducible artifacts.

Next
----

Chapter 05 will start turning these “database views” into statements with more
business realism (period closing, adjusting entries, and statement layout).

LedgerLoom Chapter 03 — Posting to the Ledger
=============================================

Big idea
--------

A **journal** records *what happened* (balanced debits and credits), entry by entry.
A **ledger** reorganizes that journal by **account** and tracks **running balances**.

This chapter turns journal lines into:

- a posted **general ledger** (per-account running balance)
- **ending balances** by account
- a **trial balance** that proves the system still balances

If Chapters 01–02 helped you *record* transactions, Chapter 03 helps you *reason* about them.

.. note::

   This chapter shows a **standalone** “posting” implementation for learning purposes.
   If you’re interested in a reusable ledger core (schema + postings fact table + balance views),
   see :doc:`ledgerloom_ch03_chart_of_accounts_schema` and :doc:`ledgerloom_ch04_general_ledger_database`,
   which use the **LedgerLoom Engine**.

What you will build
-------------------

When you run Chapter 03, it writes a complete artifact set to:

``outputs/ledgerloom/ch03``

Core accounting artifacts
~~~~~~~~~~~~~~~~~~~~~~~~~

- ``journal.csv`` — canonical journal used for posting
- ``ledger_long.csv`` — posted ledger (one row per journal line, with running balance)
- ``ledger_wide.csv`` — ledger view focused on debit/credit + running balance
- ``account_balances.csv`` — ending balance per account
- ``trial_balance.csv`` — debit/credit totals that must match

Wow / developer artifacts
~~~~~~~~~~~~~~~~~~~~~~~~~

- ``checks.md`` — PASS/FAIL invariants (entry balancing, TB totals)
- ``tables.md`` — quick tables so you can “see it” instantly
- ``diagnostics.md`` — canonical journal hash + sign conventions
- ``lineage.mmd`` — Mermaid flow of artifacts
- ``manifest.json`` — artifact inventory + sha256
- ``run_meta.json`` — reproducibility metadata
- ``summary.md`` — a one-page tour

Run it
------

From the repo root:

.. code-block:: bash

   python -m ledgerloom.chapters.ch03_posting_to_ledger --outdir outputs/ledgerloom --seed 123

You can also post an existing journal CSV:

.. code-block:: bash

   python -m ledgerloom.chapters.ch03_posting_to_ledger \
     --outdir outputs/ledgerloom \
     --in_journal path/to/your/journal.csv

(Any journal with columns ``entry_id, entry_date, memo, line_no, account, debit, credit`` will work.)

How posting works
-----------------

Every journal line has a debit and/or credit amount.

We define:

- ``signed_amount = debit - credit``
- ``normal_signed_amount`` flips the sign for accounts whose normal balance is **credit**
  (liabilities, equity, revenue), so **normal balances are positive**.

This makes running balances intuitive:

- assets/expenses usually grow positive with debits
- liabilities/equity/revenue usually grow positive with credits

Invariants (what must always be true)
-------------------------------------

Open ``checks.md`` after a run. It verifies:

1) **Each entry balances**

For every ``entry_id``:

- total debits == total credits

2) **The trial balance balances**

Across all accounts:

- total debits == total credits

If either fails, something is wrong in either:
- the source journal
- your posting logic
- your account sign conventions

Fast “wow tour” (60 seconds)
----------------------------

After running the chapter, open these in order:

1) ``summary.md`` — what you built
2) ``tables.md`` — journal, ledger, and trial balance at a glance
3) ``checks.md`` — PASS/FAIL invariants
4) ``diagnostics.md`` — canonical journal hash + sign conventions
5) ``manifest.json`` — inventory + sha256 proofs
6) ``lineage.mmd`` — data lineage you can drop into docs

Exercises
---------

1) **Break an entry on purpose**
   Edit ``journal.csv`` so one entry doesn’t balance. Re-run with ``--in_journal``.
   Confirm ``checks.md`` flips to FAIL.

2) **Add a new account**
   Add a new expense account in the journal (e.g., ``Utilities Expense``).
   Update the normal-balance mapping in the code and verify checks still PASS.

3) **Explain “normal balance”**
   Write a 3–5 sentence explanation for why liabilities are credit-normal and assets are debit-normal.

Next up
-------

In later chapters we’ll use this same artifact pattern (tables/checks/manifest/lineage)
so contributors can quickly understand the system and verify correctness.
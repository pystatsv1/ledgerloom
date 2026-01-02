LedgerLoom Chapter 01 — Journal vs event log
========================================

In paper-era accounting, transactions were recorded in a **journal** and posted to a **general ledger**.
In modern software terms, the journal is an append-only **event log**, and the ledger is a set of derived
**read models** (aggregations) like the trial balance and statements.

What you will build
-------------------

Running the chapter script:

.. code-block:: bash

   make ll-ch01

writes these artifacts to ``outputs/ledgerloom/ch01``:

- ``ledger.jsonl`` — an append-only journal (event log)
- ``trial_balance.csv`` — account balances derived from the journal
- ``income_statement.csv`` — a simple P&L derived from the trial balance
- ``balance_sheet.csv`` — a simple balance sheet (with a check row)
- ``entry_explanations.md`` — a human-readable explanation of each entry

Why debits/credits exist
------------------------

Debits and credits are a *UI convention* for expressing a constrained update:

- every entry must satisfy **sum(debits) == sum(credits)**.

In software terms, this is an invariant that makes bad states hard to represent.

Next
----

Future chapters will expand this into:

- imports from CSV (bank exports)
- configurable chart of accounts
- more realistic accrual examples (AP/AR aging)
- optional persistence backends (SQLite/DuckDB)

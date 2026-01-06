LedgerLoom — Chapter 09: Accounts Receivable lifecycle (control + subledger)
=============================================================================

Story beat
----------

Chapter 08.5 carried the **post-close** balances forward into an **opening entry** for the next period.
Now we begin Part III with a clean operational cycle: **Accounts Receivable**.

This chapter answers a very practical question:

*How do we prove the A/R subledger (open invoices) equals the general ledger (the A/R control account)?*

What you will build
-------------------

A deterministic demo that:

1. Starts from Chapter 08 post-close balances.
2. Creates an opening entry on the next period start (same idea as Chapter 08.5).
3. Posts an A/R invoice (debit A/R, credit Sales).
4. Posts cash receipts applied to invoices (debit Cash, credit A/R).
5. Produces a small A/R subledger (open items) and an aging snapshot.
6. Reconciles **A/R control** (GL) to **A/R subledger** (open items).

Run it
------

From the repo root:

.. code-block:: bash

   make ll-ch09

Or directly:

.. code-block:: bash

   python -m ledgerloom.chapters.ch09_ar_lifecycle --outdir outputs/ledgerloom --seed 123

Artifacts
---------

The runner writes to ``outputs/ledgerloom/ch09``.
Key outputs:

- ``invoices_register.csv`` – invoices issued (who, when, amount, due date)
- ``cash_receipts_register.csv`` – receipts and what invoice they apply to
- ``ar_open_items.csv`` – per-invoice open balance + days past due + aging bucket
- ``ar_control_reconciliation.csv`` – GL A/R vs subledger total (should match)
- ``trial_balance_end_period.csv`` – end-of-period trial balance including A/R activity
- ``income_statement_current_period.csv`` – current-period P&L (not closed yet)
- ``balance_sheet_current_period.csv`` – balance sheet including current-period net income
- ``invariants.json`` – engine invariants + reconciliation checks

Why the reconciliation matters
------------------------------

In real systems:

- The **subledger** is operational detail (invoice by invoice).
- The **control account** is the summarized truth used for financial statements.

If these disagree, you have a data integrity problem: missing postings, double-posted receipts,
misapplied payments, or a broken mapping between operational events and ledger entries.

In LedgerLoom, we treat the reconciliation as an invariant and make it testable.

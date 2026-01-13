Chapter 4: Closing entries and the post-close trial balance
===========================================================

At the end of an accounting period, you “reset” the temporary accounts.

Temporary accounts include:

* Revenues
* Expenses
* Dividends / Draws (depending on the business form)

The goal is to move the period’s net result into **Retained Earnings** (or the
equity-equivalent in your COA), so the next period starts clean.

In LedgerLoom workbook mode, you do **not** hand-write closing entries in a CSV.
Instead, LedgerLoom generates them deterministically from your **adjusted trial
balance**.

By the end of this chapter, you will be able to:

* explain what “closing” means and why we do it,
* read ``closing_entries.csv``,
* read ``trial_balance_post_close.csv``,
* and understand the Balance-Sheet-only invariant.

What LedgerLoom generates
-------------------------

When you run a workbook build, LedgerLoom emits two end-of-cycle artifacts:

* ``closing_entries.csv`` — a set of closing entries with ``entry_kind="closing"``
* ``trial_balance_post_close.csv`` — a post-close TB that contains only
  **Assets / Liabilities / Equity** accounts

This is a powerful learning tool:

* You can compare LedgerLoom’s generated closing entries to your textbook’s “income summary” method.
* You can verify that all temporary accounts are truly zeroed out.

Hands-on workflow
-----------------

Use the same workbook project you used for Chapters 2–3.

Step 1 — Ensure you have at least one Revenue and one Expense
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Closing is only interesting if you have temporary accounts.

If your project doesn’t yet include revenue/expense accounts, add a simple sale and an expense.
For example:

* Add to COA:

  * ``Revenue:ServiceRevenue``
  * ``Expenses:SuppliesExpense`` (or any expense you used)

* Add a sale transaction (example):

  .. code-block:: text

     T4,2026-01-05,Cleaning service paid in cash,Assets:Cash,300.00,0.00
     T4,2026-01-05,Cleaning service paid in cash,Revenue:ServiceRevenue,0.00,300.00

Now rebuild:

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch04

Step 2 — Read ``closing_entries.csv``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open:

``outputs/ch04/artifacts/closing_entries.csv``

You should see:

* revenue accounts debited to bring them to zero,
* expense accounts credited to bring them to zero,
* the net difference posted to ``Equity:RetainedEarnings``,
* dividends/draws closed to retained earnings (not through income summary).

.. admonition:: Dividends are not an expense

   Dividends reduce equity, but they do not reduce *income*.
   That’s why LedgerLoom closes dividends/draws directly to retained earnings.

Step 3 — Read ``trial_balance_post_close.csv``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open:

``outputs/ch04/artifacts/trial_balance_post_close.csv``

This trial balance should contain **only**:

* Assets
* Liabilities
* Equity (excluding dividends/draws)

If you still see Revenue or Expenses here, something is wrong: the books are not “reset.”

The invariant LedgerLoom enforces
---------------------------------

LedgerLoom enforces a strict “system reset” invariant:

* After closing, all Revenue and Expense balances must be exactly zero.
* After closing, Dividends/Draws must be exactly zero.

If the invariant fails, the build fails. That’s intentional: it prevents you from
carrying temporary balances into the next period.

Where we go next
----------------

With Chapters 1–4 in place, you now have the full *spine* of the accounting cycle:

transactions → unadjusted TB → adjustments → adjusted TB → closing → post-close TB

Later workbook chapters will build financial statements and introduce “gotcha detectors”
that catch common student errors early.

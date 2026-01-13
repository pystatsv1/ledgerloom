Chapter 3: Adjusting entries and the adjusted trial balance
===========================================================

Most businesses do not operate on a pure “cash in / cash out” basis.

At the end of the period, you record **adjusting entries** to make sure your
records reflect what was *earned* and what was *incurred* during the period.

By the end of this chapter, you will be able to:

* explain why adjustments exist (accrual vs. cash),
* compute adjustment amounts in your spreadsheet,
* export those adjustments into ``adjustments.csv``,
* and interpret ``trial_balance_adjusted.csv``.

The big idea
------------

The unadjusted trial balance is “what the ledger says after transactions.”
The adjusted trial balance is “what the ledger says after we apply accrual logic.”

In class, adjusting entries commonly fall into these buckets:

* **Deferrals** (cash happens first, expense/revenue happens later)
  * prepaid expenses, unearned revenue
* **Accruals** (expense/revenue happens first, cash happens later)
  * accrued wages, accrued interest, accounts receivable
* **Estimates**
  * depreciation, bad debt expense

LedgerLoom does not “solve” the adjustment math for you.
That work belongs in your spreadsheet (because that’s where the reasoning lives).
LedgerLoom’s job is to:

* enforce that each adjustment entry balances,
* apply it consistently to produce the adjusted trial balance,
* preserve the audit trail as versioned CSV artifacts.

Hands-on: add one adjustment
----------------------------

Use the workbook project from Chapter 2 (or the example from Chapter 0).

Step 1 — Decide your adjustment in the spreadsheet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Example adjustment: **supplies used**.

Suppose your spreadsheet says that of the supplies on hand, **$120** were used
in January.

The adjusting entry is:

* Debit **Expenses:SuppliesExpense** 120
* Credit **Assets:Supplies** 120

.. admonition:: Why this works

   * The asset (supplies on hand) goes down.
   * The expense (supplies consumed) goes up.

Step 2 — Add accounts to your chart of accounts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your COA does not already include an expense account for supplies, add one.
For example:

* ``Expenses:SuppliesExpense``

Step 3 — Put the adjustment into ``adjustments.csv``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open ``inputs/<period>/adjustments.csv`` and add:

.. code-block:: text

   entry_id,date,narration,account,debit,credit
   A1,2026-01-31,Supplies used,Expenses:SuppliesExpense,120.00,0.00
   A1,2026-01-31,Supplies used,Assets:Supplies,0.00,120.00

Step 4 — Build and compare
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch03

Now compare:

* ``outputs/ch03/artifacts/trial_balance_unadjusted.csv``
* ``outputs/ch03/artifacts/trial_balance_adjusted.csv``

You should see:

* Supplies (asset) is **$120 lower** after the adjustment.
* SuppliesExpense (expense) appears with a **$120 debit balance**.

Common adjustment mistakes
--------------------------

* **Forgetting to add the account to the COA** → LedgerLoom can’t classify it.
* **Putting the adjustment in transactions.csv** → keep transactions and adjustments separate.
* **Reversing debit/credit** → the adjusted TB moves in the wrong direction.

Next chapter
------------

In Chapter 4, you will close temporary accounts and produce a **post-close trial
balance** that contains only balance sheet accounts.

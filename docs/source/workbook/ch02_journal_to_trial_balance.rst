Chapter 2: From journal lines to an unadjusted trial balance
============================================================

In Chapter 1, you proved the accounting equation using a spreadsheet.
In this chapter, you connect that idea to the *double-entry system* you will use
for the rest of the course.

By the end of this chapter, you will be able to:

* write balanced journal entries in ``transactions.csv``,
* explain what LedgerLoom’s ``entries.csv`` represents,
* explain what a trial balance is (and what it *isn’t*),
* reconcile your spreadsheet totals to ``trial_balance_unadjusted.csv``.

What is a journal entry?
------------------------

A **journal entry** records one business event.

* It has **two or more lines**.
* The total debits equal the total credits.
* Each line affects exactly one account.

LedgerLoom workbook mode stores journal lines in a CSV with these columns:

* ``entry_id`` — groups the lines that belong to the same transaction
* ``date`` — the transaction date
* ``narration`` — a plain-English description
* ``account`` — an account name from your chart of accounts (e.g. ``Assets:Cash``)
* ``debit`` / ``credit`` — numeric amounts (exactly one should be non-zero per line)

.. admonition:: The one invariant you never violate

   For each ``entry_id``:

   **sum(debit) == sum(credit)**

   If you violate this, LedgerLoom stops immediately.

What is a trial balance?
------------------------

A **trial balance** is a report that lists every account and its ending balance.

* It does **not** prove the books are correct.
* It **does** prove that total debits = total credits across the ledger.

In LedgerLoom workbook mode:

* **Unadjusted TB** = opening + transactions
* **Adjusted TB** = opening + transactions + adjustments

The trial balance is a bridge between:

* your detailed journal lines (what happened), and
* financial statements (the summary view).

Hands-on workflow
-----------------

You can do this chapter in one of two ways:

* use the runnable example from Chapter 0 and edit the CSVs, or
* create a new workbook project with ``ledgerloom init --profile workbook``.

Option A — Start from the example project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy the example folder somewhere you can edit it (so you don’t modify the
LedgerLoom repo itself):

.. code-block:: bash

   cp -r examples/workbook/ch01_startup ~/ledgerloom_homework/ch02
   cd ~/ledgerloom_homework/ch02

Option B — Create a fresh workbook project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom init --profile workbook ch02_trial_balance
   cd ch02_trial_balance

Either way, you should now have:

* ``ledgerloom.yaml``
* ``config/chart_of_accounts.yaml``
* ``inputs/<period>/transactions.csv``
* ``inputs/<period>/adjustments.csv``

Step 1 — Fill in ``transactions.csv``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For practice, add 4–6 simple transactions (owner investment, a sale, a purchase,
and a payment).

Then run:

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch02

Step 2 — Read the artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open the folder:

``outputs/ch02/artifacts/``

Start with:

* ``entries.csv`` — LedgerLoom’s cleaned, canonical view of your journal lines
* ``trial_balance_unadjusted.csv`` — balances by account after transactions

What you are looking for:

* Every account you used appears on the trial balance.
* The trial balance “looks like” what your spreadsheet says.

Step 3 — Reconcile to your spreadsheet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In your spreadsheet, you likely have a table with account totals.
That’s exactly what the trial balance is.

If something doesn’t match:

* Find the account that differs.
* Look at the lines in ``entries.csv`` for that account.
* Check for a swapped debit/credit, a wrong account, or a typo in the amount.

Common beginner mistakes (and what LedgerLoom catches)
------------------------------------------------------

* **Unbalanced entry** (debits ≠ credits): build stops immediately.
* **Unknown account name**: check stops because the COA can’t classify it.
* **Two-sided line** (both debit and credit non-zero): check stops.
* **Sign confusion**: your spreadsheet and LedgerLoom disagree; fix the journal line.

Next chapter
------------

In Chapter 3, you will add **adjusting entries** and learn why the adjusted trial
balance is the real “end-of-period truth” for statements.

What you'll learn
-----------------
- Write balanced journal entries in ``transactions.csv``
- Explain what LedgerLoom’s ``entries.csv`` represents
- Explain what a trial balance is (and what it isn't)
- Reconcile your spreadsheet totals to ``trial_balance_unadjusted.csv``

Key accounting terms
--------------------
- **Journal entry:** a set of lines with the same ``entry_id``. Balanced entries are the first invariant.
- **Debit / credit:** a *direction* on an account, not a value judgement.
  A quick normal-balance cheat sheet:

  - **Increase with debits:** Assets, Expenses, Dividends
  - **Increase with credits:** Liabilities, Equity, Revenue

- **Posting:** taking journal lines and “posting” them into the ledger (grouped by account).
- **Ledger:** the running history of each account after posting.
- **Trial balance (unadjusted):** balances after regular transactions **before** end-of-period adjustments.
  A trial balance can balance and still be wrong (wrong account or wrong period), so you still need reasoning.

What to do in your spreadsheet
------------------------------
1) Enter the chapter’s transactions as journal lines.
2) Ensure each ``entry_id`` is balanced (total debits = total credits).
3) Produce your spreadsheet trial balance.

Export CSVs
-----------
Export:

- ``inputs/<period>/transactions.csv``

(Adjustments come in Chapter 3, so ``adjustments.csv`` can be empty for now.)

Run LedgerLoom
--------------
.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch02

What to look at
---------------
- ``entries.csv``: normalized entries (LedgerLoom's parse of your journal)
- ``trial_balance_unadjusted.csv``: your transactions-only trial balance

For definitions and “how to read it”, see :doc:`workbook_artifacts_reference`.

Compare against the answer key
------------------------------
If you want to confirm your work:

- :doc:`workbook_check_your_work_pack`

Common mistakes
---------------
- Entry not balanced (LedgerLoom will flag this)
- Using an account that isn't in your chart of accounts
- Sign errors (debit/credit swapped)
- Spreadsheet TB includes an account total that doesn’t tie to your journal lines

Downloads
---------
- :download:`Completed Ch02 spreadsheet (XLSX) <../_static/ledgerloom_workbook_completed_ch02_journal_to_trial_balance.xlsx>`
- :download:`Reference outputs pack (ZIP) <../_static/ledgerloom_workbook_reference_outputs_ch02_journal_to_trial_balance.zip>`

Next chapter
------------
Continue to :doc:`ch03_adjusting_entries`.

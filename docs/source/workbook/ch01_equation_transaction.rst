Ch01B — Accounting equation + transactions
============================================

What you'll learn
-----------------
- Describe how each business event changes A / L / E
- Translate a business event into a *balanced* journal entry (two or more lines)
- Use LedgerLoom to confirm you didn’t “balance by accident”

Key accounting terms
--------------------
- **Assets:** resources the business controls (cash, equipment, inventory).
- **Liabilities:** obligations the business owes (loans, accounts payable).
- **Equity:** the owner’s residual claim (what’s left after liabilities).
- **Revenue:** value earned from providing goods/services during the period.
- **Expense:** costs incurred to earn revenue during the period.
- **Net income:** ``revenue − expenses`` for the period; it increases equity.
- **Owner capital / retained earnings:** where net income ultimately accumulates (depends on entity type/course).
- **Dividends / draws:** distributions to the owner. They **reduce equity** but are **not** an expense.

What to do in your spreadsheet
------------------------------
For each event, do two passes:

1) **Equation pass**: explain the change in Assets / Liabilities / Equity
2) **Journal pass**: write the corresponding debit/credit lines

Export CSVs
-----------
Export (or edit directly) the journal lines:

- ``inputs/<period>/transactions.csv``

If you are using the workbook project created in Chapter 0, this is already in place.

Run LedgerLoom
--------------
From your workbook project folder:

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch01

What to look at
---------------
- ``entries.csv``: what LedgerLoom ingested (grouped by ``entry_id``)
- ``trial_balance_unadjusted.csv``: your “transactions-only” trial balance

If your spreadsheet totals don’t match the unadjusted trial balance, you have a reconciliation problem
(not a “LedgerLoom problem”). Use :doc:`workbook_troubleshooting`.

Compare against the answer key
------------------------------
This chapter’s concepts are applied using the same Chapter 0/1 startup dataset.
Use the Ch01 packs if you want a known-good reference:

- :doc:`workbook_check_your_work_pack`

Common mistakes
---------------
- Treating an asset purchase as an expense (e.g., supplies vs supplies expense)
- Recording one-sided entries (missing the second line)
- Mixing up account roots (Assets vs Expenses vs Equity)

Downloads
---------
Use the Ch01 startup packs:

- :download:`Completed Ch01 spreadsheet (XLSX) <../_static/ledgerloom_workbook_completed_ch01_startup.xlsx>`
- :download:`Reference outputs pack (ZIP) <../_static/ledgerloom_workbook_reference_outputs_ch01_startup.zip>`

Next chapter
------------
Continue to :doc:`ch02_journal_to_trial_balance`.

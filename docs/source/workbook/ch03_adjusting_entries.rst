Chapter 3: Adjusting entries and the adjusted trial balance
===========================================================

Most businesses do not operate on a pure “cash in / cash out” basis.
At the end of the period, you record **adjusting entries** so your books reflect what was earned and incurred.

What you'll learn
-----------------
- Explain why adjustments exist (accrual vs. cash)
- Compute adjustment amounts in your spreadsheet
- Export adjustments into ``adjustments.csv``
- Interpret ``trial_balance_adjusted.csv``

What to do in your spreadsheet
------------------------------
1) Start from your Chapter 2 unadjusted trial balance.
2) Compute the adjustment amount(s) (example: supplies used, prepaid expiring, accrued revenue).
3) Write the adjusting journal entry lines.

Export CSVs
-----------
Export:

- ``inputs/<period>/transactions.csv`` (same as Ch02)
- ``inputs/<period>/adjustments.csv`` (new for this chapter)

Run LedgerLoom
--------------
.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch03

What to look at
---------------
- ``trial_balance_unadjusted.csv``: before adjustments
- ``trial_balance_adjusted.csv``: after adjustments

Your spreadsheet’s adjusted trial balance should match LedgerLoom’s adjusted trial balance
account-by-account (within rounding rules you control in the spreadsheet).

Compare against the answer key
------------------------------
If you want a known-good reference:

- :doc:`workbook_check_your_work_pack`

Common mistakes
---------------
- Putting adjustments in ``transactions.csv`` instead of ``adjustments.csv``
- Using the wrong date (adjustments are typically period-end)
- Adjusting the wrong account (asset vs expense)
- Recording the right adjustment with the wrong sign

Downloads
---------
- :download:`Completed Ch03 spreadsheet (XLSX) <../_static/ledgerloom_workbook_completed_ch03_adjusting_entries.xlsx>`
- :download:`Reference outputs pack (ZIP) <../_static/ledgerloom_workbook_reference_outputs_ch03_adjusting_entries.zip>`

Next chapter
------------
Continue to :doc:`ch04_closing_and_post_close`.

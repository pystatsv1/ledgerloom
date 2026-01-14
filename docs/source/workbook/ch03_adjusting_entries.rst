Ch03 — Adjusting entries
==========================

.. admonition:: Month-end reality check (Jan 31, 2026)

   At the end of January, **Harborview Bike Repair** does a quick month-end close.
   Cash transactions alone don’t capture what really happened during the period, so we add a
   few **adjusting entries** that match revenue/expenses to January.

   The canonical adjustments in this chapter are small on purpose, but they mirror real
   bookkeeping decisions:

   - **A001 (Supplies used):** a quick count shows $150 of supplies were consumed during January.
   - **A002 (Depreciation):** one month of wear on equipment ($50).
   - **A003 (Utilities accrued):** the utility bill hasn’t been paid yet, but $75 was incurred.
   - **A004 (Revenue accrued):** $200 of service was earned but not yet billed/collected.

What you'll learn
-----------------
- Explain why adjustments exist (accrual vs. cash)
- Compute adjustment amounts in your spreadsheet
- Export adjustments into ``adjustments.csv``
- Interpret ``trial_balance_adjusted.csv``

Key accounting terms
--------------------
- **Accrual accounting:** record revenue when earned and expenses when incurred (not when cash moves).
- **Adjusting entry:** an end-of-period entry that updates balances to match accrual reality.
  Adjustments often change an **asset or liability** *and* a **revenue or expense**.
- **Accrual vs deferral:**

  - **Accrued expense:** expense happened, cash/payment is later (creates a liability).
  - **Accrued revenue:** revenue earned, cash/collection is later (creates an asset).
  - **Prepaid expense:** cash paid first, expense recognized later (asset → expense over time).
  - **Unearned revenue:** cash received first, revenue recognized later (liability → revenue over time).

- **Depreciation:** allocating the cost of a long-lived asset over time (expense).
  Many systems use a separate **contra-asset** (Accumulated Depreciation), but this workbook keeps the
  chart of accounts small and credits ``Assets:Equipment`` directly.

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

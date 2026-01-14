Workbook Learning Path (Spreadsheet + LedgerLoom)
=================================================

This is the **main path** for the workbook: you do the accounting in your spreadsheet,
then use LedgerLoom to verify it and produce clean CSV artifacts you can compare.

The loop you will repeat
------------------------

1) **Draft** in Sheets/Excel (transactions + adjustments + optional closing).
2) **Export CSVs** using the workbook template headers.
3) Run:

   .. code-block:: bash

      ledgerloom check --project .
      ledgerloom build --project . --run-id run1

4) **Reconcile**: compare your spreadsheet totals to LedgerLoom outputs. Fix mistakes, re-run.

Where to start
--------------

If you are brand new, do this in order:

- :doc:`student_quick_start` (install + your first run)
- :doc:`ch01_startup` (a runnable, known-good project)
- :doc:`ch02_journal_to_trial_balance` (journal → TB)
- :doc:`ch03_adjusting_entries` (accrual adjustments → adjusted TB)
- :doc:`ch04_closing_and_post_close` (closing → post-close TB)

If you want to learn the accounting cycle **without any tooling first**, use the
Spreadsheet-First track: :doc:`workbook_spreadsheet_first_overview`.

What “success” looks like
-------------------------

- ``ledgerloom check`` produces a review package under ``outputs/check/<period>/``.
- ``ledgerloom build --run-id run1`` produces a full run folder under ``outputs/run1/``.
- Your spreadsheet and LedgerLoom artifacts should agree on totals (trial balance and post-close TB).

Next: learn the output files
----------------------------

Before you go deeper, skim:

- :doc:`workbook_artifacts_reference` — what each CSV output means
- :doc:`workbook_troubleshooting` — common mistakes and how to recover quickly

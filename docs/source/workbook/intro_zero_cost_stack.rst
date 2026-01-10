Introduction: The zero-cost stack
=================================

If you are starting an “Intro to Financial Accounting” course, you’ve probably got:

- a textbook,
- a calculator,
- and a spreadsheet open…

…and you’re hoping you didn’t miss a sign, a row, or a formula.

This workbook introduces **The Hybrid Method**:

- **Google Sheets** for drafting (visual + flexible + free)
- **LedgerLoom** for verification (rigid + strict + free)

LedgerLoom is like a spell-checker for accounting.
It stops you when your work violates the double-entry invariant, and it produces
standard artifacts (postings, trial balance, financial statements) you can compare
to your sheet.

What you need
-------------

- A free Google account (Google Sheets)
- Python 3.10+ (already required by LedgerLoom)
- LedgerLoom v0.2.0

Install LedgerLoom
------------------

.. code-block:: bash

   pip install ledgerloom

Create a homework project
-------------------------

.. code-block:: bash

   ledgerloom init my_homework
   cd my_homework

This creates a small project folder with:

- ``ledgerloom.yaml`` (project config)
- ``config/chart_of_accounts.yaml`` (your chart)
- ``config/mappings/`` (your mapping rules)
- ``inputs/<period>/`` (bank feed CSVs go here)
- ``outputs/<run_id>/`` (build artifacts land here)



What you'll learn
-----------------
- Install LedgerLoom from PyPI (student workflow)
- Create a workbook project with ``ledgerloom init --profile workbook``
- Understand where outputs go (``outputs/check`` vs ``outputs/<run_id>``)
- Run the end-to-end workflow: inputs → check → build → artifacts

Key accounting terms
--------------------
These terms show up in every chapter:

- **Transaction:** a business event you record (sale, purchase, payment, owner investment).
- **Account:** a “bucket” for a type of value (Cash, Supplies Expense, Owner Capital).
- **Chart of Accounts (CoA):** the full list of accounts you’re allowed to use.
  LedgerLoom uses colon-separated names like ``Assets:Cash`` and ``Revenue:ServiceRevenue``.
- **Journal entry:** a group of two or more lines that share an ``entry_id``.
  The total debits must equal the total credits for that ``entry_id``.
- **Debit / credit:** the two sides of an entry. They are **not** “good” or “bad”.
  Most courses teach **normal balances**:

  - Assets, Expenses, and Dividends usually increase with **debits**.
  - Liabilities, Equity, and Revenue usually increase with **credits**.

- **Trial balance:** a list of ending balances by account. If every entry is balanced,
  total debits = total credits, but you can still be “wrong” (wrong account, wrong timing).

What to do in your spreadsheet
------------------------------
1) Open the Workbook template (or your course sheet).
2) Enter the “Startup” transactions for the period.
3) (Optional) compute one simple adjustment (e.g., supplies used).

Export CSVs
-----------
Export these CSVs from your spreadsheet tabs:

- ``inputs/<period>/transactions.csv`` (journal lines)
- ``inputs/<period>/adjustments.csv`` (end-of-period adjustments)

The exact column headers matter. If you’re unsure, use:

- :download:`Workbook template (XLSX) <../_static/ledgerloom_workbook_template.xlsx>`
- :download:`Template CSV headers (XLSX) <../_static/ledgerloom_workbook_template_csv_headers.xlsx>`

Run LedgerLoom
--------------
Create a new workbook project (once):

.. code-block:: bash

   ledgerloom init --profile workbook my_books
   cd my_books

Then verify and build:

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch01

Where outputs go
----------------
- ``ledgerloom check`` (by itself) writes to ``outputs/check/<period>/``
- ``ledgerloom build --run-id ch01`` writes to ``outputs/ch01/`` and includes:

  - ``outputs/ch01/check/`` (the check report for this run)
  - ``outputs/ch01/trust/`` (manifest + run metadata)
  - ``outputs/ch01/artifacts/`` (the canonical CSV outputs you will compare)

What to look at
---------------
Start with these artifacts:

- ``entries.csv`` (normalized entries LedgerLoom ingested)
- ``trial_balance_unadjusted.csv`` (transactions only)
- ``trial_balance_adjusted.csv`` (transactions + adjustments)
- ``closing_entries.csv`` and ``trial_balance_post_close.csv`` (end-of-cycle)

For a plain-English guide to each artifact, see :doc:`workbook_artifacts_reference`.

Compare against the answer key
------------------------------
Every workbook chapter has a canonical dataset under ``examples/workbook/<chapter_slug>/``.
If you want a known-good reference:

- see :doc:`workbook_check_your_work_pack` (completed spreadsheet + reference outputs zips)

Common mistakes
---------------
- Wrong CSV headers (extra spaces, renamed columns)
- Debits/credits not balanced within an ``entry_id``
- Accounts that don’t match the chart of accounts (typos / wrong root)
- Confusing ``outputs/check`` (standalone check) with ``outputs/<run_id>`` (build run)

Downloads
---------
- :download:`Completed Ch01 spreadsheet (XLSX) <../_static/ledgerloom_workbook_completed_ch01_startup.xlsx>`
- :download:`Reference outputs pack (ZIP) <../_static/ledgerloom_workbook_reference_outputs_ch01_startup.zip>`

Next chapter
------------
Continue to :doc:`ch01_equation_transaction`.

Workbook Project Layout (Files and Folders)
===========================================

This page explains how a LedgerLoom **workbook project** is organized on disk.

You do *not* need to be a programmer. Think of this as “a folder with a few files.”

Big picture: inputs → outputs
-----------------------------

- You put **inputs** (CSV tables + a small config file) in a project folder.
- LedgerLoom reads them and writes **outputs** (artifact CSVs) into an ``outputs/`` folder.

A typical workbook project looks like this:

.. code-block:: text

   my_books/
     ledgerloom.yaml
     config/
       chart_of_accounts.yaml
     inputs/
       2026-01/
         transactions.csv
         adjustments.csv
     outputs/
       run1/
         artifacts/
           entries.csv
           trial_balance_unadjusted.csv
           trial_balance_adjusted.csv
           closing_entries.csv
           trial_balance_post_close.csv
         manifest.json
         run_meta.json

What each part means
--------------------

``ledgerloom.yaml``
  The project configuration. It tells LedgerLoom what “profile” you’re using
  (for this workbook: **workbook**) and where your inputs live.

``config/chart_of_accounts.yaml``
  Your chart of accounts. This is where accounts are typed (Assets, Liabilities, Equity,
  Revenue, Expenses, Dividends/Draws).

``inputs/<period>/transactions.csv``
  Your transaction table (the “raw events” you enter or export from a sheet).

``inputs/<period>/adjustments.csv``
  Your adjusting entries table (often empty at the start of Chapter 1).

``outputs/<run_id>/artifacts/``
  The CSV results LedgerLoom generates. These are meant to be opened in Excel/Sheets
  and compared to your workbook.

What is a run_id?
-----------------

A ``run_id`` is just a name for “this run of the pipeline.”

Example:

- ``run1`` (first attempt)
- ``run2_fix_sign_error`` (after you fix a mistake)
- ``week3_submission`` (when you submit)

Using a new run_id is useful because you keep old results for comparison.

What are “artifacts” and why do we care?
----------------------------------------

Artifacts are the “official outputs” of the accounting pipeline.

They help you answer:

- What did my journal entries *normalize into*?
- What do postings look like account-by-account?
- Do my temporary accounts close properly?
- Does the post-close TB contain only Balance Sheet accounts?

Artifacts are also easy to grade and review because:

- they are stable
- they are shareable
- they can be regenerated from inputs

Common workflow (what you actually do)
--------------------------------------

1) Create a project folder:

.. code-block:: bash

   ledgerloom init --profile workbook my_books

2) Run checks (fast sanity checks):

.. code-block:: bash

   ledgerloom check --project my_books --run-id run1

3) Build artifacts:

.. code-block:: bash

   ledgerloom build --project my_books --run-id run1

4) Open artifacts in Excel/Sheets and compare.

If something is wrong, don’t panic
----------------------------------

LedgerLoom failing a check is not “bad”—it’s feedback.

Typical beginner mistakes:

- a debit/credit swap
- a sign flip (positive vs negative)
- an account name typo
- an account placed in the wrong type (e.g., Revenue vs Asset)

Fix the input table, run again with a new ``run_id``, and compare.

Next: Student Quick Start
-------------------------

Go to:

:doc:`student_quick_start`


Introduction: The zero-cost stack
=================================

If you are starting an “Intro to Financial Accounting” course, you’ve probably got:

* a textbook,
* a calculator,
* and a spreadsheet open…

…and you’re hoping you didn’t miss a sign, a row, or a formula.

This workbook introduces **The Hybrid Method**:

* **Google Sheets or Excel** for drafting (visual, flexible, familiar)
* **LedgerLoom** for verification (rigid, strict, deterministic)

Think of LedgerLoom like a spell-checker for accounting:

* It stops you when your work violates the double-entry invariant.
* It produces standard artifacts (entries + trial balances) you can compare to your sheet.

What you need
-------------

You do **not** need paid software.

* A spreadsheet (Google Sheets, Excel, LibreOffice)
* Python 3.10+ (Windows/macOS/Linux)
* LedgerLoom (installed from PyPI)

.. tip:: Using Git Bash on Windows

   The command examples in this workbook use a POSIX-style shell.
   On Windows, Git Bash is a great choice (and it matches what we use in class).

Install LedgerLoom
------------------

.. code-block:: bash

   python -m pip install --upgrade pip
   python -m pip install ledgerloom

If the ``ledgerloom`` command is not found, you can always run:

.. code-block:: bash

   python -m ledgerloom --help

Create a workbook project
-------------------------

LedgerLoom uses a small project folder with a config file (``ledgerloom.yaml``) and
CSV inputs.

.. code-block:: bash

   ledgerloom init --profile workbook my_homework
   cd my_homework

This creates:

* ``ledgerloom.yaml`` (project config)
* ``config/chart_of_accounts.yaml`` (your chart of accounts)
* ``inputs/<period>/transactions.csv`` (journal lines)
* ``inputs/<period>/adjustments.csv`` (adjusting entries)
* ``outputs/<run_id>/`` (artifacts per run)

From there, your workflow is simple:

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id run-01

Next: go to :doc:`ch01_startup` to run a known-good example and learn what the
output folders mean.

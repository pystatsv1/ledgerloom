Workbook Chapter 0 — Setup and a Runnable Startup Project
=========================================================

This chapter is the **setup** chapter.

By the end, you will be able to:

* install LedgerLoom from PyPI on Windows, macOS, or Linux,
* run a known-good example project,
* understand the *inputs → verification → artifacts* workflow,
* and know where to look when something goes wrong.

LedgerLoom is not a replacement for your spreadsheet. It’s a verifier.
You do the thinking and drafting in Sheets/Excel; LedgerLoom checks the invariants
(balanced entries, stable totals) and produces canonical artifacts you can compare
to your sheet.

What you need
-------------

* **Python 3.10+** (3.11 or 3.12 recommended).
* A terminal:

  * **Windows:** Git Bash (recommended) or PowerShell
  * **macOS/Linux:** Terminal

Install LedgerLoom (PyPI)
-------------------------

You can install LedgerLoom in two common ways:

Option A — Virtual environment (recommended for students)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a folder for your course work, then:

.. code-block:: bash

   # create a virtual environment
   python -m venv .venv

   # activate it
   # macOS/Linux:
   source .venv/bin/activate
   # Windows (Git Bash):
   source .venv/Scripts/activate

   # install LedgerLoom
   python -m pip install --upgrade pip
   python -m pip install ledgerloom

Verify:

.. code-block:: bash

   python -m ledgerloom --help

Option B — pipx (nice CLI install)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you already use ``pipx`` (it installs CLI tools in isolated environments):

.. code-block:: bash

   pipx install ledgerloom
   ledgerloom --help

.. admonition:: If you see “command not found”

   Use the module form instead:

   .. code-block:: bash

      python -m ledgerloom --help

Your first runnable project (in the repo)
-----------------------------------------

LedgerLoom’s documentation includes a runnable example project in the repository.
This is what keeps the docs honest: the docs literally include the real files.

The example lives here::

   examples/workbook/ch01_startup/

Run it
------

From the LedgerLoom repository root, you can run the example by pointing
``--project`` at the example folder.

.. code-block:: bash

   python -m ledgerloom check --project examples/workbook/ch01_startup
   python -m ledgerloom build --project examples/workbook/ch01_startup --run-id demo

Where do outputs go?
--------------------

LedgerLoom writes build artifacts under the project folder:

* ``outputs/<run_id>/artifacts/`` — CSV artifacts you can open in Excel/Sheets
* ``outputs/<run_id>/manifest.json`` — a “trust manifest” that records file hashes

For the example above, look in::

   examples/workbook/ch01_startup/outputs/demo/artifacts/

You should see:

* ``entries.csv``
* ``trial_balance_unadjusted.csv``
* ``trial_balance_adjusted.csv``
* ``closing_entries.csv``
* ``trial_balance_post_close.csv``

.. admonition:: Why “trust manifests” matter

   In accounting (and in real analytics work), you want the same inputs to produce
   the same outputs every time. LedgerLoom records hashes of every artifact so you
   can prove your build is deterministic.

Project config: ``ledgerloom.yaml``
-----------------------------------

This file declares the project’s build profile (here: ``workbook``), the accounting
period, and where inputs live.

.. literalinclude:: ../../../examples/workbook/ch01_startup/ledgerloom.yaml
   :language: yaml

Chart of accounts: ``config/chart_of_accounts.yaml``
----------------------------------------------------

The chart of accounts (COA) is the *type system* for your bookkeeping.
LedgerLoom uses it to classify accounts into Assets / Liabilities / Equity /
Revenue / Expenses.

.. literalinclude:: ../../../examples/workbook/ch01_startup/config/chart_of_accounts.yaml
   :language: yaml

Workbook inputs: ``transactions.csv``
-------------------------------------

In workbook mode, your “transactions” input is a CSV version of your journal entries.
Each transaction has one or more lines; the lines for a single ``entry_id`` must
balance (debits = credits).

.. literalinclude:: ../../../examples/workbook/ch01_startup/inputs/2026-01/transactions.csv
   :language: text

Workbook inputs: ``adjustments.csv``
------------------------------------

Adjustments are also journal entries (same schema), usually created at period-end.
In Chapter 3, you’ll learn how to compute adjustment amounts in your spreadsheet,
then export them to this CSV.

.. literalinclude:: ../../../examples/workbook/ch01_startup/inputs/2026-01/adjustments.csv
   :language: text

The example README (what students actually do)
----------------------------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/README.md
   :language: text

Troubleshooting checklist
-------------------------

If something fails, check these in order:

1. **Are you pointing at a project folder?**
   ``ledgerloom build`` expects a folder containing ``ledgerloom.yaml``.
2. **Is your CSV comma-separated and UTF-8?**
   Export from Sheets as CSV. Don’t use semicolons.
3. **Do debits equal credits per entry_id?**
   LedgerLoom will stop if any entry is unbalanced.
4. **Did you activate your virtual environment?**
   If you installed LedgerLoom in a venv, you must activate it first.

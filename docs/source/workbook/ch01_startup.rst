Workbook Chapter 1 — Runnable Startup Project
=============================================

This page is a **copy/paste runnable** workbook project that you can execute locally.

The goal is to make the workbook workflow executable *in the repository* and *in the docs*:

- Students draft transactions and adjustments in CSV (from Sheets/Excel exports).
- LedgerLoom verifies the accounting-cycle invariants and emits deterministic artifacts.
- The docs stay in sync with the real project files via ``literalinclude``.

Project folder
--------------

The runnable example lives here in the repository::

   examples/workbook/ch01_startup/

Run it
------

From the example folder:

.. code-block:: bash

   python -m ledgerloom check --project .
   python -m ledgerloom build --project . --run-id demo

You should see artifacts written under ``outputs/`` including:

- ``entries.csv``
- ``trial_balance_unadjusted.csv``
- ``trial_balance_adjusted.csv``
- ``closing_entries.csv``
- ``trial_balance_post_close.csv``

Configuration: ``ledgerloom.yaml``
----------------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/ledgerloom.yaml
   :language: yaml

Chart of accounts: ``config/chart_of_accounts.yaml``
----------------------------------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/config/chart_of_accounts.yaml
   :language: yaml

Inputs: ``transactions.csv``
----------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/inputs/2026-01/transactions.csv
   :language: text

Inputs: ``adjustments.csv``
---------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/inputs/2026-01/adjustments.csv
   :language: text

Example README (from the project folder)
----------------------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/README.md
   :language: text

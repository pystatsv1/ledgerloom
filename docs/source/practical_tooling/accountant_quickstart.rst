Accountant quickstart (copy/paste)
==================================

This page is written in an "accountant-first" voice. It's also intentionally shaped so you can
copy/paste it into a README later.


What you need
-------------

* A LedgerLoom project folder (contains ``ledgerloom.yaml``)
* A chart of accounts YAML (valid account codes)
* One or more bank-feed CSV files for a period


0) Create a project (one-time)
------------------------------

If you are starting from scratch, create a project skeleton:

.. code-block:: bash

   ledgerloom init my_books

Then ``cd`` into the project folder:

.. code-block:: bash

   cd my_books


1) Put files in a period folder
-------------------------------

Create a folder for the period you are working on:

.. code-block:: text

   inputs/2026-01/

Drop your CSV exports into that folder.


2) Run the gatekeeper
---------------------

From the project root (the folder that contains ``ledgerloom.yaml``):

.. code-block:: bash

   ledgerloom check

LedgerLoom will write a check run folder (by default):

.. code-block:: text

   outputs/check/2026-01/


3) Open the report and fix issues
---------------------------------

Open:

* ``outputs/check/2026-01/checks.md`` (what to fix first)
* ``outputs/check/2026-01/staging_issues.csv`` (exception list you can filter/sort)

Key column: ``source_row_number``
   This is the **original row number in the source CSV** (1-based relative to the first data row).
   It lets you find the problematic record quickly in Excel.


4) Re-run until errors are gone
-------------------------------

``ledgerloom check`` returns:

* exit code ``0`` when there are **no errors** (warnings may be present)
* exit code ``1`` when **errors** are present

Warnings usually mean "uncategorized" rows that landed in a suspense account; you can decide
whether to treat them as acceptable for now or tighten your mapping rules.


Next step: build (coming)
-------------------------

The next major command is ``ledgerloom build`` (planned for v0.2.0). It will:

* post staged entries into a ledger (balanced double-entry)
* generate a trial balance + statements
* write a run directory with trust artifacts (manifest + run metadata)


4) Create a run folder (snapshot + check)
-----------------------------------------

Once your check results look good, you can create a **run folder** that snapshots your inputs/configs.

.. code-block:: bash

   ledgerloom build --run-id demo

This writes:

* ``outputs/demo/source_snapshot/`` (copy of your inputs + configs)
* ``outputs/demo/check/`` (the gatekeeper results for this run)

If check finds errors, build exits non-zero but keeps the run folder so you can inspect what happened.

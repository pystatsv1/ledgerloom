Build a run (snapshot + gatekeeper)
===================================

The :command:`ledgerloom build` command creates a **run folder** under your project's
``outputs/`` directory.

In PR07a, build is intentionally simple:

1. Create ``outputs/<run_id>/``
2. Snapshot source files into ``outputs/<run_id>/source_snapshot/``
3. Run :command:`ledgerloom check` and write results into ``outputs/<run_id>/check/``

This makes every run **self-contained**: even if you edit or delete the original CSVs next week,
the run folder still contains the exact inputs and configs used at the time you built it.

Command
-------

From the project root (the folder that contains ``ledgerloom.yaml``):

.. code-block:: bash

   ledgerloom build --run-id demo

Useful flags
------------

``--run-id``
   Choose a stable run folder name (great for support and testing).

``--no-snapshot``
   Skip copying source files. Not recommended if you want an auditable run.

What gets created
-----------------

``outputs/<run_id>/``
   The run directory.

``outputs/<run_id>/source_snapshot/``
   A copy of:

   * ``ledgerloom.yaml``
   * everything under ``config/`` (chart of accounts, mappings, etc.)
   * all input CSV files matched by your configured sources for the period

``outputs/<run_id>/check/``
   The gatekeeper outputs for this run (``checks.md``, ``staging.csv``, ``staging_issues.csv``).

Next steps (PR07b/PR07c)
------------------------

* PR07b adds **trust artifacts** (``trust/run_meta.json`` and ``trust/manifest.json``).
* PR07c adds the core **accounting outputs** (postings, trial balance, statements).

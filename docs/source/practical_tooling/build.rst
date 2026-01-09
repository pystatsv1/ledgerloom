Build a run (snapshot + gatekeeper)
===================================

The :command:`ledgerloom build` command creates a **run folder** under your project's
``outputs/`` directory.

Build is intentionally simple:

1. Create ``outputs/<run_id>/``
2. Snapshot source files into ``outputs/<run_id>/source_snapshot/``
3. Run :command:`ledgerloom check` and write results into ``outputs/<run_id>/check/``
4. Emit trust artifacts into ``outputs/<run_id>/trust/``
5. When check passes, write accounting artifacts into ``outputs/<run_id>/artifacts/`` (currently: ``postings.csv`` and ``trial_balance.csv``)

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

``outputs/<run_id>/trust/``
   Trust artifacts for this run (``run_meta.json`` and ``manifest.json``).

``outputs/<run_id>/artifacts/``
   Accounting artifacts for this run. Currently: ``postings.csv`` and ``trial_balance.csv`` (written only when check passes).

Next steps
----------

* Build already writes two accounting outputs (``artifacts/postings.csv`` and ``artifacts/trial_balance.csv``).
* Next planned artifacts: statements, plus richer reporting UX.

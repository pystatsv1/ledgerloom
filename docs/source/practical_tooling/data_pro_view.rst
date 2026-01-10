Data pro view
=============

This page explains LedgerLoom's outputs as **analysis-ready tables** and suggests a simple workflow
for exploring a run in pandas or your BI tool of choice.

Where the data lives
--------------------

A ``ledgerloom build`` run writes four key folders:

- ``source_snapshot/`` — the exact inputs/configs used (for reproducibility)
- ``check/`` — staging tables + issue lists (data quality / pipeline diagnostics)
- ``artifacts/`` — postings + trial balance + statements (accounting outputs)
- ``trust/`` — hashes for everything tracked (audit + reproducibility)

If you're doing analytics, you will usually start with:

- ``artifacts/postings.csv`` (the fact table)
- ``artifacts/trial_balance.csv`` (a derived snapshot)
- ``check/staging.csv`` and ``check/staging_issues.csv`` (data quality context)

Core tables
-----------

Postings (fact table)
^^^^^^^^^^^^^^^^^^^^^

``artifacts/postings.csv`` is the canonical fact table for analysis. Each row is a posting line
(debit or credit) with stable identifiers and deterministic ordering.

Typical columns include:

- ``date`` — posting date (normalized)
- ``entry_id`` — stable identifier for the originating entry
- ``line_no`` — stable line number within the entry
- ``account`` — chart-of-accounts code/name
- ``debit`` / ``credit`` — amounts (non-negative, in the project currency)
- optional dimensions (e.g., ``department``) when configured

Trial balance (snapshot)
^^^^^^^^^^^^^^^^^^^^^^^^^

``artifacts/trial_balance.csv`` provides balances by account for the run period. It is derived from
postings and is useful for quick sanity checks and reporting rollups.

Statements
^^^^^^^^^^

LedgerLoom writes simple CSV statements:

- ``artifacts/income_statement.csv``
- ``artifacts/balance_sheet.csv``

These are intentionally minimal; many data pros will prefer to re-aggregate from postings and the COA
metadata.

Check tables (pipeline diagnostics)
-----------------------------------

- ``check/staging.csv`` — normalized raw rows (what LedgerLoom read)
- ``check/staging_issues.csv`` — machine-readable issues (errors and warnings)
- ``artifacts/unmapped.csv`` — rows that landed in suspense because no mapping rule matched
- ``artifacts/reclass_template.csv`` — helper template for reclassifying suspense rows

These tables let you answer: *what did we ingest, what failed validation, and what needs mapping work?*

Quickstart: load a run into pandas
----------------------------------

.. code-block:: python

   import pandas as pd
   from pathlib import Path

   run_dir = Path("examples/real_world_scenario/outputs/run-a")

   postings = pd.read_csv(run_dir / "artifacts" / "postings.csv")
   tb = pd.read_csv(run_dir / "artifacts" / "trial_balance.csv")
   issues = pd.read_csv(run_dir / "check" / "staging_issues.csv")

   # Common first checks
   print(postings.head())
   print(tb.sort_values("account").head())
   print(issues["severity"].value_counts())

Reproducibility tips
--------------------

- Keep the entire ``outputs/<run_id>/`` folder when sharing results.
- Use the manifest as your audit trail: it proves the inputs/configs and outputs match.
- Prefer re-aggregating from postings for analytics so you can validate derived tables yourself.

If you want a ready-to-run example, start with:

.. code-block:: bash

   ledgerloom check --project examples/real_world_scenario
   ledgerloom build --project examples/real_world_scenario --run-id run-a

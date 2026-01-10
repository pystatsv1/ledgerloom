Practical tooling overview
==========================

LedgerLoom ships a small CLI that turns *messy real-world inputs* (bank CSVs + simple mapping rules)
into *deterministic, reviewable accounting artifacts*.

A LedgerLoom **project** is just a folder with:

- ``ledgerloom.yaml`` (project configuration)
- ``config/chart_of_accounts.yaml`` (your chart of accounts)
- ``config/mappings/`` (optional: mapping rules)
- ``inputs/<period>/`` (your source CSV files)
- ``outputs/`` (generated run folders + check reports)

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** A repeatable workflow: import → review exceptions → produce postings + trial balance + statements.

   **Developer:** A deterministic build pipeline with a trust manifest you can hash, diff, and put in CI.

   **Data pro:** Clean, columnar outputs (postings + statements) that you can join, model, and visualize.

Quick start
-----------

.. code-block:: bash

   # Create a new project folder
   ledgerloom init demo_books

   # Validate your inputs + mappings (no "run" folder yet)
   ledgerloom check --project demo_books

   # Build a run folder (snapshot + check + trust + artifacts)
   ledgerloom build --project demo_books --run-id run-2026-01

Run folders (what ``build`` writes)
-----------------------------------

``ledgerloom build`` creates an *immutable* run directory:

- ``outputs/<run_id>/source_snapshot/`` — copy of the inputs/config used for the run
- ``outputs/<run_id>/check/`` — the check report produced during this build
- ``outputs/<run_id>/trust/`` — the trust manifest for the run
- ``outputs/<run_id>/artifacts/`` — postings, trial balance, and statements

Determinism + the trust anchor
------------------------------

LedgerLoom is designed so that **the trust manifest hash is stable**:

- If you run the same project inputs/config twice, the bytes of
  ``outputs/<run_id>/trust/manifest.json`` are the same (even with different ``run_id``),
  so the SHA-256 is the same.
- This lets you treat the manifest hash as a *content-addressed trust anchor*.

See also:

- :doc:`init`
- :doc:`check`
- :doc:`build`
- :doc:`reclass_workflow`

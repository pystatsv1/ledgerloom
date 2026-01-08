Practical tool overview
=======================

LedgerLoom is both:

* a teaching project (accounting concepts for developers), and
* a practical workflow for turning messy inputs into trustworthy accounting outputs.

The practical tool is intentionally **simple and deterministic**. The core idea is:

1. Put raw files in a period folder.
2. Run a gatekeeper check to get a clean, actionable exception list.
3. Build postings + reports from staged entries.
4. Keep a complete audit trail (hashed inputs, stable outputs).


What a LedgerLoom project looks like
------------------------------------

A LedgerLoom project is just a folder:

.. code-block:: text

   my_books/
     ledgerloom.yaml
     config/
       chart_of_accounts.yaml
       mappings/            # (future) mapping packs
     inputs/
       2026-01/
         chase_checking.csv
         visa_card.csv
     outputs/
       check/
         2026-01/
           checks.md
           staging.csv
           staging_issues.csv


Commands
--------

``ledgerloom check``
    Stages + validates inputs *before* building anything. It produces a markdown report and a CSV
    exception list (this is the main "gatekeeper" experience).

``ledgerloom build`` (coming)
    Ingests inputs, posts balanced entries, produces a trial balance and financial statements, and
    writes trust artifacts (a run directory with stable, hashed outputs).


The trust goal
--------------

LedgerLoom aims for outputs that are stable across operating systems and reruns:

* deterministic file ordering
* normalized LF newlines
* a manifest describing inputs/configs/outputs with hashes
* a run metadata file capturing the configuration + environment

These guarantees make it easier to:

* review changes in Git,
* reproduce the same run later,
* and explain "where the numbers came from".

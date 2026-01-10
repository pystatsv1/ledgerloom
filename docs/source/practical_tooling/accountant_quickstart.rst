Accountant quickstart
=====================

This is the fastest path to “use LedgerLoom for real bookkeeping work.”

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** Treat this like a lightweight month-end workflow.

   **Developer:** Treat this like a reproducible pipeline with stable artifacts.

   **Data pro:** Treat this like a repeatable ETL job that outputs analysis-ready tables.

0) Create a project
-------------------

.. code-block:: bash

   ledgerloom init demo_books

1) Put your CSVs in the inputs folder
-------------------------------------

Copy your bank CSV files into:

- ``demo_books/inputs/<period>/``

The default period is set in ``demo_books/ledgerloom.yaml``.

2) Set up your chart of accounts
--------------------------------

Edit:

- ``demo_books/config/chart_of_accounts.yaml``

Add (or rename) accounts you actually use.

3) Run a check (review package)
-------------------------------

.. code-block:: bash

   ledgerloom check --project demo_books

Review:

- ``outputs/check/<period>/checks.md``
- ``outputs/check/<period>/unmapped.csv``

4) Encode reclasses as rules
----------------------------

Use the reclass workflow:

- :doc:`reclass_workflow`

5) Build a run folder (deliverables + trust)
--------------------------------------------

.. code-block:: bash

   ledgerloom build --project demo_books --run-id run-2026-01

Deliverables are in:

- ``demo_books/outputs/run-2026-01/artifacts/``

Next: if your workflow includes closing entries, that comes after postings + statements.

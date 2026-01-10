Data professional view (tables + analysis)
==========================================

LedgerLoom’s output is designed to be loaded into pandas, DuckDB, or your BI tool of choice.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** Think of postings as the “detailed GL,” and statements as summaries.

   **Developer:** Think of postings as the fact table, with COA as a dimension table.

   **Data pro:** Think of postings as a clean, analysis-ready event stream.

Where outputs live
------------------

For a run id like ``run-2026-01``, build writes:

- ``outputs/run-2026-01/artifacts/postings.csv``
- ``outputs/run-2026-01/artifacts/trial_balance.csv``
- ``outputs/run-2026-01/artifacts/income_statement.csv``
- ``outputs/run-2026-01/artifacts/balance_sheet.csv``

Postings (fact table)
---------------------

The postings table is the canonical “long” format:

- one row per posting line
- stable sort order
- suitable for aggregation and reconciliation

Typical analysis workflow
-------------------------

.. code-block:: python

   import pandas as pd

   postings = pd.read_csv("outputs/run-2026-01/artifacts/postings.csv")
   tb = pd.read_csv("outputs/run-2026-01/artifacts/trial_balance.csv")

   # Example: total spend by account
   spend = (
       postings.loc[postings["account_type"] == "expense"]
       .groupby(["account_code", "account_name"], as_index=False)["amount"]
       .sum()
       .sort_values("amount", ascending=False)
   )

Join to COA
-----------

Your chart of accounts file is a natural dimension table. Keep codes stable, and you’ll be able to
trend categories over time with confidence.

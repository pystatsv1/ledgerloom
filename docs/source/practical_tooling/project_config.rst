Project configuration
=====================

LedgerLoom projects are configured with a single YAML file (typically
``ledgerloom.yaml``) that is validated against a **versioned schema**.

The goal of v0.2.0 is that an accountant can:

* initialize a project (no Python)
* drop CSVs into an ``inputs/`` folder
* edit YAML mappings
* run ``ledgerloom check`` and ``ledgerloom build``

Schema ID
---------

The top-level document **must** include::

   schema_id: ledgerloom.project_config.v1

This allows LedgerLoom to evolve without breaking existing projects.

Minimal example
---------------

The smallest useful config looks like::

   schema_id: ledgerloom.project_config.v1
   project:
     name: "My Company"
     period: "2026-01"
     currency: "USD"
   chart_of_accounts: "config/chart_of_accounts.yaml"
   sources: []
   outputs:
     root: "outputs"

Bank feed source (v1)
---------------------

For v0.2.0, the only supported source type is a simple bank-feed CSV adapter.
It maps a raw CSV to balanced double-entry :class:`~ledgerloom.core.Entry`
objects.

Example::

   sources:
     - source_type: "bank_feed.v1"
       name: "Chase Checking"
       # Pattern is evaluated within ``inputs/<period>/`` by default.
       # (So you typically **do not** include the inputs folder prefix here.)
       file_pattern: "chase_*.csv"
       default_account: "Assets:US:Chase:Checking"
       date_format: "%m/%d/%Y"
       columns:
         date: "Posting Date"
         description: "Description"
         amount: "Amount"
       # Optional amount parsing overrides (useful for EU formats).
       amount_thousands_sep: ","
       amount_decimal_sep: "."
       invert_amount_sign: true
       suspense_account: "Expenses:Uncategorized"
       rules:
         - pattern: "Starbucks|Peets"
           account: "Expenses:MealsAndEntertainment"

Next steps
----------

* ``ledgerloom check`` provides the gatekeeper experience (staging + validation).
* ``ledgerloom build`` creates a run folder (snapshot + check + trust) and, when check passes,
  writes accounting artifacts:

  * ``outputs/<run_id>/artifacts/postings.csv``
  * ``outputs/<run_id>/artifacts/trial_balance.csv``
  * ``outputs/<run_id>/artifacts/income_statement.csv``
  * ``outputs/<run_id>/artifacts/balance_sheet.csv``

* Next planned artifacts: closing entries + post-close statements (plus subledgers like AR/AP/inventory).

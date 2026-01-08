Chart of Accounts YAML
======================

LedgerLoom uses a Chart of Accounts (COA) as a **schema**:

* It defines which account codes are valid.
* It records account metadata (type, rollups, contra flags).
* It enables early validation: "this CSV row references an unknown account".

For the practical-tool workflow, LedgerLoom reads the COA from a versioned YAML
file and converts it into the engine's COA model.


File format (v1)
----------------

Your COA YAML must include a schema id and a list of accounts.

.. code-block:: yaml

   schema_id: ledgerloom.chart_of_accounts.v1
   accounts:
     - code: Assets:Cash
       name: Cash
       account_type: ASSET

     - code: Revenue:Sales
       name: Sales revenue
       account_type: REVENUE

     - code: Expenses:Meals
       name: Meals & entertainment
       account_type: EXPENSE

Optional fields
~~~~~~~~~~~~~~~

Each account may also include optional metadata:

.. code-block:: yaml

   - code: Assets:AccumDepr
     name: Accumulated depreciation
     account_type: ASSET
     is_contra: true
     rollup_code: Assets:FixedAssets
     is_active: true
     track_department: false
     track_project: false
     description: "Contra-asset used for depreciation."


Validation
----------

LedgerLoom runs the engine's COA validation rules (duplicates, required fields,
normal-side consistency) and returns a list of validation messages.

In later PRs, the ``ledgerloom check`` command will also use the COA to flag
unknown account codes **before** posting anything to the ledger.

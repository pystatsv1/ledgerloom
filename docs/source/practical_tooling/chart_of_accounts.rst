Chart of accounts (config/chart_of_accounts.yaml)
=================================================

The chart of accounts (COA) defines the set of accounts LedgerLoom is allowed to post to.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** This is your GL account list: codes, names, and normal classification.

   **Developer:** This is a schema for validation (unknown accounts are errors).

   **Data pro:** This is the dimension table you’ll join to postings for reporting.

Example
-------

.. code-block:: yaml

   schema_id: ledgerloom.chart_of_accounts.v1

   accounts:
     - code: 1000
       name: Cash
       type: asset
     - code: 4000
       name: Consulting income
       type: income
     - code: 6500
       name: Office supplies
       type: expense

Field notes
-----------

- ``code`` should be unique. Keep it stable once you have historical data.
- ``type`` is used for statement classification (e.g., income vs expense).
- Add accounts freely as your business grows, but avoid renumbering existing codes.

See also: :doc:`project_config`.

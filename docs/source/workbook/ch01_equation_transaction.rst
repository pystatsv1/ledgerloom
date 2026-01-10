Chapter 1: The equation & the transaction
=========================================

**Subtitle:** The physics of business

Before we touch debits/credits, we learn the law that *must* always hold:

.. math::

   \text{Assets} = \text{Liabilities} + \text{Equity}

LedgerLoom exists to enforce this law.

The assignment: “Sparkle Cleaners”
----------------------------------

Scenario
^^^^^^^^

On January 1, 2026, Sarah opens **Sparkle Cleaners**, a local cleaning business.

Record these transactions:

1. **Jan 1:** Sarah invests **$10,000** cash into the business bank account.
2. **Jan 2:** The business buys cleaning equipment for **$3,000** (paid from the bank).
3. **Jan 3:** The business buys cleaning supplies for **$500** (paid from the bank).

Your goal
^^^^^^^^^

After each transaction, show that the equation remains balanced.

Draft the solution in Google Sheets
-----------------------------------

Create a sheet with these asset sub-columns:

- Cash
- Equipment
- Supplies

And these right-side columns:

- Liabilities (none yet in this chapter)
- Equity (Owner capital)

Work each transaction step-by-step:

1) Owner investment (Jan 1)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Cash increases by 10,000 (asset up)
- Capital increases by 10,000 (equity up)

2) Equipment purchase (Jan 2)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Cash decreases by 3,000
- Equipment increases by 3,000

This is a pure asset swap.

3) Supplies purchase (Jan 3)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Cash decreases by 500
- Supplies increases by 500

The gotcha: asset vs expense
----------------------------

Many students instinctively record the $500 as an expense (“we bought stuff to use”).

For this chapter, treat the supplies as an **asset**:

- On Jan 3, the supplies are sitting on a shelf.
- They become an expense later, when used up.

.. admonition:: Translation box — what a spreadsheet hides

   In a spreadsheet, you can “make it balance” by changing a cell.
   LedgerLoom won’t let you: the postings must sum to zero, every time.

Verify with LedgerLoom (v0.2.0 workflow)
----------------------------------------

In LedgerLoom v0.2.0, we verify using the practical tool pipeline:

**bank feed CSV → mapping rules → postings → trial balance → statements**

Step 1 — Initialize a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom init sparkle_cleaners
   cd sparkle_cleaners

Step 2 — Add accounts to your chart
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Edit ``config/chart_of_accounts.yaml`` and add these accounts (keeping the file valid YAML):

.. code-block:: yaml

   accounts:
     Assets:
       Cash:
       Equipment:
       Supplies:
     Equity:
       Capital:
     Expenses:
       Supplies:

Step 3 — Create a tiny bank feed CSV
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Date,Description,Amount
2026-01-01,Owner investment,10000.00
2026-01-02,Buy equipment,-3000.00
2026-01-03,Buy supplies,-500.00

Step 4 — Add mapping rules
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create ``config/mappings/checking.yaml``:

.. code-block:: yaml

   version: 1
   default_account: Assets:Cash
   rules:
     - when:
         description_contains: "Owner investment"
       to_account: Equity:Capital

     - when:
         description_contains: "equipment"
       to_account: Assets:Equipment

     - when:
         description_contains: "supplies"
       to_account: Assets:Supplies

Step 5 — Run check, then build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch01

Now open these artifacts:

- ``outputs/ch01/artifacts/postings.csv``
- ``outputs/ch01/artifacts/trial_balance.csv``
- ``outputs/ch01/artifacts/balance_sheet.csv``

Reconciling with your Google Sheet
----------------------------------

Your sheet and LedgerLoom should agree on the ending balances:

- Cash = 6,500
- Equipment = 3,000
- Supplies = 500
- Capital = 10,000

If they don’t match, treat it like a programming bug:

- locate the first place the two diverge,
- inspect the mapping rule or sign,
- fix it,
- re-run ``ledgerloom build``.

That’s the Hybrid Method: **draft fast, verify strict, reconcile to proof**.

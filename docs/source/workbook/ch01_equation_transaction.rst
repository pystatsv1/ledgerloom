Chapter 1: The equation & the transaction
=========================================

**Subtitle:** The physics of business

Before we touch debits/credits, we learn the law that *must* always hold:

.. math::

   \text{Assets} = \text{Liabilities} + \text{Equity}

LedgerLoom exists to enforce this law.

In this workbook, you will *draft* the accounting in a spreadsheet, then *verify*
it with LedgerLoom.

Why do this?

* A spreadsheet is great for exploration.
* A verifier is great for **proof**.
* When the two agree, you know you didn’t “balance by accident.”

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

In the *workbook* profile, we verify using the accounting-cycle artifacts that
match what you do in class:

**transactions.csv → (optional) adjustments.csv → entries → trial balances → closing**

Step 1 — Initialize a workbook project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom init --profile workbook sparkle_cleaners
   cd sparkle_cleaners

.. tip::

   If your terminal can’t find the ``ledgerloom`` command, use:

   .. code-block:: bash

      python -m ledgerloom init --profile workbook sparkle_cleaners

Step 2 — Add the accounts you need
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open ``config/chart_of_accounts.yaml`` and make sure it contains at least:

* ``Assets:Cash``
* ``Assets:Equipment``
* ``Assets:Supplies``
* ``Equity:OwnerCapital``

.. admonition:: Keep it simple

   In Chapter 1 we *do not* record expenses yet. Supplies are an **asset** here.
   (You’ll see supplies become an expense later, when used up.)

Step 3 — Enter the journal lines in ``transactions.csv``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open ``inputs/<period>/transactions.csv`` (the folder name is your period, e.g. ``2026-01``)
and enter these lines:

.. code-block:: text

   entry_id,date,narration,account,debit,credit
   T1,2026-01-01,Owner investment,Assets:Cash,10000.00,0.00
   T1,2026-01-01,Owner investment,Equity:OwnerCapital,0.00,10000.00
   T2,2026-01-02,Buy equipment,Assets:Equipment,3000.00,0.00
   T2,2026-01-02,Buy equipment,Assets:Cash,0.00,3000.00
   T3,2026-01-03,Buy supplies,Assets:Supplies,500.00,0.00
   T3,2026-01-03,Buy supplies,Assets:Cash,0.00,500.00

Each ``entry_id`` groups the lines of a single transaction. LedgerLoom enforces
that each entry balances.

Step 4 — Run check, then build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id ch01

Now open these artifacts under ``outputs/ch01/artifacts/``:

* ``entries.csv`` (your cleaned, canonical entries)
* ``trial_balance_unadjusted.csv``

.. tip::

   If you are using Excel/Sheets, you can *import* the trial balance CSV and
   compare it directly to your spreadsheet totals.

Reconciling with your Google Sheet
----------------------------------

Your sheet and LedgerLoom should agree on the ending balances:

* Cash = 6,500
* Equipment = 3,000
* Supplies = 500
* OwnerCapital = 10,000

If they don’t match, treat it like a programming bug:


* locate the first place the two diverge,
* inspect the transaction lines (wrong account? wrong sign? swapped debit/credit?),
* fix the CSV,
* re-run ``ledgerloom build``.

That’s the Hybrid Method: **draft fast, verify strict, reconcile to proof**.

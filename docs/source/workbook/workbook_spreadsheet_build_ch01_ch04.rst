Spreadsheet-First Build Guide (Ch01–Ch04)
=========================================

Goal
----

You are going to build the accounting-cycle workbook *manually* in a spreadsheet first:

**Transactions → Journal → Postings → Trial Balance → Adjustments → Adjusted TB → Closing → Post-close TB**

Then you will run LedgerLoom on the same inputs and compare results.

This is the fastest way to learn, because you already know what the data means *before* a tool verifies it.

What data to use
----------------

Use the canonical data shown here:

- :doc:`workbook_data_pack_ch01_startup`

You should not invent your own numbers yet. Use the same dataset so your results match the book and LedgerLoom.

Spreadsheet setup (works in Google Sheets or Excel)
---------------------------------------------------

Create a new spreadsheet file. Add these tabs:

- ``COA`` (chart of accounts)
- ``Journal`` (general journal)
- ``Postings`` (optional, can be auto-generated with formulas)
- ``TB_Unadjusted`` (unadjusted trial balance)
- ``Adjustments`` (adjusting entries journal)
- ``TB_Adjusted`` (adjusted trial balance)
- ``Closing`` (closing entries journal)
- ``TB_PostClose`` (post-close trial balance)

Conventions (important)
-----------------------

**1) Debit/Credit are separate positive-number columns.**  
Do *not* enter negative numbers in debit/credit columns.

**2) One journal entry can have multiple lines.**  
A “single transaction” often produces 2+ journal lines.

**3) Always verify the invariant:**
Total Debits = Total Credits (for each entry, and for the whole journal).

**4) Dates:** Use ISO dates like ``2026-01-05`` (YYYY-MM-DD).

Step 1 — COA tab
----------------

Copy the chart of accounts (from the data pack) into your ``COA`` tab.

Recommended columns:

- ``account_id`` (or number)
- ``account_name``
- ``account_type`` (Asset/Liability/Equity/Revenue/Expense)
- ``normal_side`` (Debit or Credit)

Step 2 — Journal tab (transactions)
-----------------------------------

Create these columns in ``Journal``:

- ``date``
- ``entry_id`` (you make this up: JE-001, JE-002, …)
- ``description``
- ``account``
- ``debit``
- ``credit``

Now, take each row from the canonical ``transactions.csv`` and translate it into journal lines.

How to translate “events” into journal lines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A transaction/event is a *story*; a journal entry is the *accounting encoding* of that story.

Example pattern:

- If cash increases → debit Cash
- If cash decreases → credit Cash
- If a liability increases → credit that liability
- If an expense increases → debit that expense
- If revenue increases → credit revenue

**Your job (as a student) is to choose the correct accounts.**  
LedgerLoom’s job is to verify you didn’t break the rules (balanced entries, consistent TB, proper closing).

Checkpoint A (Journal balances)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At the bottom of the Journal sheet:

- Sum of Debit column
- Sum of Credit column

They must match exactly.

Step 3 — TB_Unadjusted
----------------------

Make a Trial Balance table with columns:

- ``account``
- ``debits``
- ``credits``
- ``balance``

How to compute balances (generic approach)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each account:

- total_debits = SUMIF(Journal!account == this_account, Journal!debit)
- total_credits = SUMIF(Journal!account == this_account, Journal!credit)
- balance = total_debits - total_credits

Then place the balance on the correct side:

- If balance > 0 → show in Debit column
- If balance < 0 → show ABS(balance) in Credit column

Checkpoint B (TB balances)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Total Debits in TB = Total Credits in TB.

If not, your journal is wrong.

Step 4 — Adjustments + TB_Adjusted (Chapter 3)
-----------------------------------------------

Create an ``Adjustments`` tab with the same columns as Journal:

- ``date``, ``entry_id``, ``description``, ``account``, ``debit``, ``credit``

You will add adjusting entries here (accruals/deferrals/estimates).

Then compute ``TB_Adjusted`` by combining:

Journal totals + Adjustments totals.

Checkpoint C:
~~~~~~~~~~~~~

Adjusted TB Debits = Adjusted TB Credits.

Step 5 — Closing + TB_PostClose (Chapter 4)
-------------------------------------------

Closing entries “reset” temporary accounts:

- Revenue → closed to Retained Earnings
- Expenses → closed to Retained Earnings
- Dividends/Draws → closed to Retained Earnings

Create a ``Closing`` tab (same columns again).

Then compute ``TB_PostClose``:

Adjusted TB + Closing entries.

Checkpoint D (the big invariant):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Post-close TB contains ONLY balance sheet accounts:**

- Assets, Liabilities, Equity (including Retained Earnings)
- No Revenue, no Expenses, no Dividends/Draws

If you still see Revenue/Expense accounts on the post-close TB, closing is incomplete.

Where LedgerLoom fits
---------------------

Once you can produce these tables manually, LedgerLoom becomes simple:

- You supply the canonical CSV inputs
- LedgerLoom produces canonical artifacts (entries, TBs, closing, post-close TB)
- LedgerLoom verifies invariants you may accidentally break in a spreadsheet

Next: run the runnable project
------------------------------

Go to :doc:`student_quick_start` and run the exact same dataset through LedgerLoom.

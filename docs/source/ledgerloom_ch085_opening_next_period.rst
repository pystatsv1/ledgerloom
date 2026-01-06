LedgerLoom Chapter 08.5 — Opening the Next Period
=================================================

This bridge chapter connects Chapter 08 (closing) to Part III (operational cycles).

After you *close* the books for a period, you have a **post-close** trial balance where:

- Temporary accounts (Revenue / Expenses / IncomeSummary) are **zeroed**
- Permanent accounts (Assets / Liabilities / Equity) carry the ending balances forward
- Retained earnings captures the period’s net income (via the close)

Chapter 08.5 shows the next story beat:

**post-close → opening the next period** (and proving continuity)

What you will build
-------------------

You will generate a single **Opening Balances** entry dated on the first day of the next period
that reproduces the permanent-account balances from Chapter 08’s post-close trial balance.

You will also emit proof artifacts that:

- Reconcile **post-close TB** (Ch08) to **opening TB** (Ch08.5)
- Confirm that **Revenue/Expenses open at 0.00**
- Confirm **RetainedEarnings continuity**

How it works
------------

1. Compute Chapter 08 post-close trial balance (in-memory, deterministic).
2. Convert each permanent-account balance into a debit or credit line, based on normal balance
   conventions (Assets are debit-normal; Liabilities/Equity are credit-normal).
3. Compile the opening entry through the same engine, producing:
   - postings
   - opening trial balance
   - opening balance sheet
4. Produce an explicit reconciliation against the Ch08 post-close trial balance.

How to run
----------

From the project root::

   make ll-ch085

Artifacts
---------

This runner writes deterministic outputs to::

   outputs/ledgerloom/ch085/

Key files:

- ``trial_balance_post_close.csv`` — the Ch08 post-close TB (source-of-truth)
- ``trial_balance_opening.csv`` — the opening TB for the next period
- ``reconciliation_post_close_vs_opening.csv`` — per-account diffs (should all be 0.00)
- ``retained_earnings_continuity.csv`` — focused proof line for retained earnings
- ``invariants.json`` + ``manifest.json`` — engine invariants and artifact hashes

Next
----

Part III begins with **Chapter 09 — Accounts Receivable lifecycle**.

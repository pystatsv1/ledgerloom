LedgerLoom Chapter 08 — Closing as a controlled transformation
==============================================================

Chapter 07 ended with the **adjusted close**:

- start from the unadjusted event log (what you had on the deadline)
- append **adjusting entries** (late-arriving data)
- verify the trial balance + statements are still consistent

So now we have a new question:

**How do we reset Revenue and Expenses for the next period without erasing the period we just measured?**

That’s **closing**.

Closing is a pipeline step
--------------------------

LedgerLoom treats closing exactly like good data engineering treats a production transformation:

- **Append-only**: we add closing entries; we do not mutate the past
- **Deterministic**: closing is computed from the adjusted trial balance
- **Auditable**: we emit artifacts that prove the close happened correctly

What closing *does* (and does not do)
-------------------------------------

Closing does **not** change the economics of the period.
It only moves the period’s net income from temporary accounts into permanent Equity.

After closing:

- all **Revenue** accounts have a **zero** balance
- all **Expense** accounts have a **zero** balance
- the period’s **NetIncome** is transferred into **Equity** (RetainedEarnings)

IncomeSummary approach (B)
--------------------------

There are two common ways to close:

A) Close each Revenue/Expense directly to RetainedEarnings (skips the intermediate step)

B) Close Revenue and Expenses into **IncomeSummary**, then close IncomeSummary into **RetainedEarnings**

LedgerLoom uses **B** here because it is more explainable:

- IncomeSummary is an explicit intermediate “stage” (like a materialized view)
- It creates a clean invariant: **IncomeSummary must be zero after close**
- It makes it easy to test and audit *why* Equity moved

Artifacts produced
------------------

When you run Chapter 08, LedgerLoom writes both the *before* and *after* snapshots:

- ``postings_adjusted.csv`` — postings after adjustments (same story as Ch07)
- ``trial_balance_adjusted.csv`` — adjusted trial balance (Revenue/Expenses still open)
- ``income_statement_adjusted.csv`` — the period result (Revenue - Expenses)

Then it appends closing entries (IncomeSummary approach) and shows the result:

- ``postings_closing.csv`` — postings from closing entries only
- ``closing_entries_register.csv`` — closing entry metadata (period, posted_at, reason)
- ``trial_balance_post_close.csv`` — post-close trial balance (temporary accounts reset)
- ``balance_sheet_post_close.csv`` — equation check **A = L + E** holds without NetIncome term

And two “proof” tables:

- ``temp_accounts_before_after.csv`` — Revenue/Expenses/IncomeSummary go to zero
- ``equity_rollforward.csv`` — Equity increases by exactly NetIncome

Finally:

- ``closing_checklist.json`` — pass/fail checks for the close
- ``invariants.json`` — engine invariants for adjusted + post-close ledgers
- ``manifest.json`` — SHA256 checksums for every artifact (trust engineering)

How to run
----------

From the repo root:

.. code-block:: bash

   make ll-ch08

Or run the module directly:

.. code-block:: bash

   python -m ledgerloom.chapters.ch08_closing_controlled_transformation \
     --outdir outputs/ledgerloom --seed 123

Key learning goals
------------------

- **Accountants**: see closing as a transparent, testable step (not magic)
- **Developers**: see closing as an idempotent transformation driven by a source-of-truth table
- **Data professionals**: see closing as a reproducible pipeline stage with a manifest + checksums


Workbook Artifacts Reference
============================

LedgerLoom produces two kinds of outputs:

1) **Check outputs** (fast feedback) — written by ``ledgerloom check``
2) **Run outputs** (a full snapshot) — written by ``ledgerloom build --run-id <run_id>``

Check outputs (``outputs/check/<period>/``)
-------------------------------------------

These files help you fix problems *before* you build a run folder:

- ``checks.md``  
  A human-readable report: what LedgerLoom found, and what to do next.

- ``staging.csv``  
  Your inputs normalized into a consistent table format.

- ``staging_issues.csv``  
  Row-level problems (missing fields, invalid dates, bad numbers).

- ``unmapped.csv``  
  Rows LedgerLoom could not map cleanly (often an account name mismatch).

- ``reclass_template.csv``  
  A “fill-in-the-blanks” template used for reclassing/mapping workflows.

Run outputs (``outputs/<run_id>/artifacts/``)
---------------------------------------------

These are the canonical workbook artifacts you compare against your spreadsheet:

- ``entries.csv``  
  Your journal entries in a normalized, deterministic format.

- ``trial_balance_unadjusted.csv``  
  Trial balance after posting **transactions** only.

- ``trial_balance_adjusted.csv``  
  Trial balance after posting **transactions + adjustments**.

- ``closing_entries.csv``  
  The closing entry set that resets temporary accounts (revenue/expenses/dividends).

- ``trial_balance_post_close.csv``  
  Post-close trial balance (balance-sheet accounts only).

Where “trust” fits (``outputs/<run_id>/trust/``)
------------------------------------------------

LedgerLoom also writes a trust package (hashes + manifests) so a run folder is a
reproducible snapshot.

As a student, you usually only need this when:

- you’re submitting a “run folder” as proof, or
- you want to confirm you built against the intended inputs.

If you’re curious, start with:

- ``trust/run_meta.json`` — what was built, when, and from which sources
- ``trust/manifest.json`` — the list of artifacts and their hashes

How to use this page while working
----------------------------------

If something breaks:

1) run ``ledgerloom check``  
2) open ``outputs/check/<period>/checks.md``  
3) fix the first error you see, then re-run

If you’re unsure which output to compare:

- use **trial balances** to validate totals
- use **entries.csv** to validate the “shape” of the journal (dates, accounts, signs)

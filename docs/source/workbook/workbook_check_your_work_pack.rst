Optional: Check Your Work Pack (Ch01 Startup)
=============================================

This workbook is meant to be a *learning* experience, not a “gotcha” test.
If you have a low tolerance for frustration (or you just want to confirm you’re on the right track),
use the downloads below to compare your work against a known-good reference.

What you get
------------

1) **Completed spreadsheet (XLSX)** — the Chapter 1 “Startup” transactions already filled in,
   using the exact `transactions.csv` column headers LedgerLoom expects.

   - :download:`Download: completed Ch01 spreadsheet (XLSX) <../_static/ledgerloom_workbook_completed_ch01_startup.xlsx>`

2) **Reference outputs (ZIP)** — a small “check your work” pack containing:

   - the canonical exported inputs: ``inputs/transactions.csv`` and ``inputs/adjustments.csv``
   - the LedgerLoom artifacts produced by ``ledgerloom build``:

     - ``entries.csv``
     - ``trial_balance_unadjusted.csv``
     - ``trial_balance_adjusted.csv``
     - ``closing_entries.csv``
     - ``trial_balance_post_close.csv``

   - plus ``trust/run_meta.json`` and ``trust/manifest.json``

   - :download:`Download: reference outputs pack (ZIP) <../_static/ledgerloom_workbook_reference_outputs_ch01_startup.zip>`

How to use it
-------------

**Option A — “I just want to see the right data”**

Download the completed XLSX and compare it to your spreadsheet:

- same column names
- same rows
- same debit/credit amounts

**Option B — “I want to verify my LedgerLoom run”**

1. Run your project:

   .. code-block:: bash

      ledgerloom build --project path/to/your_project --run-id myrun

2. Open the artifacts folder:

   ``path/to/your_project/outputs/myrun/artifacts``

3. Compare your generated CSVs against the ones in the ZIP pack.

Notes for instructors
---------------------

If you are using LedgerLoom for graded work, consider telling students *when* they may use this pack
(e.g., “after submitting your own attempt”).

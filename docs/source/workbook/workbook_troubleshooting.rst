Workbook Troubleshooting
========================

This page is a student-friendly checklist for the most common problems.

I ran ``ledgerloom check`` and it failed
----------------------------------------

Start here:

1) Open ``outputs/check/<period>/checks.md``.
2) Fix the *first* issue listed (later issues often cascade from earlier ones).
3) Run ``ledgerloom check`` again.

I can’t find my outputs
-----------------------

- ``ledgerloom check`` writes to: ``outputs/check/<period>/``
- ``ledgerloom build --run-id run1`` writes to: ``outputs/run1/``

Your workbook artifacts live in:

- ``outputs/<run_id>/artifacts/``

I see ``unmapped.csv``
----------------------

This usually means LedgerLoom didn’t recognize something in your inputs (often an
account name mismatch).

Do this:

1) Open ``outputs/check/<period>/unmapped.csv``.
2) Compare the ``account`` values to ``config/chart_of_accounts.yaml``.
3) Fix the spelling / punctuation / account root (``Assets:``, ``Liabilities:``, etc.).
4) Re-run ``ledgerloom check``.

My trial balance doesn’t balance
--------------------------------

If your spreadsheet trial balance debits ≠ credits:

- Look for a sign error (debit entered as credit or vice versa).
- Look for a missing “pair” row in a journal entry (every entry must balance).
- Compare your spreadsheet journal lines against ``outputs/<run_id>/artifacts/entries.csv``.

I used ``--run-id`` with ``check`` and got an error
---------------------------------------------------

``--run-id`` belongs to ``build``, not ``check``:

.. code-block:: bash

   ledgerloom check --project .
   ledgerloom build --project . --run-id run1

LedgerLoom says an account root is invalid
------------------------------------------

LedgerLoom expects account names to start with one of these roots:

- ``Assets:``
- ``Liabilities:``
- ``Equity:``
- ``Revenue:``
- ``Expenses:``

Example:

- ✅ ``Assets:Cash``
- ❌ ``Cash`` (missing root)

Still stuck?
------------

- Re-run ``ledgerloom check`` and read ``checks.md`` carefully.
- If you are working from a workbook chapter, compare against the
  :doc:`workbook_check_your_work_pack`.
- If you think it’s a bug, open an issue on GitHub with:

  - your LedgerLoom version (``ledgerloom --version``)
  - the ``checks.md`` file
  - a minimal set of inputs that reproduces the issue

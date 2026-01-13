Spreadsheet Walkthrough: Chapters 1–4 (No LedgerLoom)
=====================================================

This page is a practical “how-to” for completing Chapters 1–4 in a spreadsheet.

The goal is to produce the same artifacts LedgerLoom will later verify:

- Unadjusted Trial Balance
- Adjusted Trial Balance
- Closing Entries
- Post-close Trial Balance

**Optional template (download):** :download:`LedgerLoom Workbook spreadsheet template (XLSX) <../_static/ledgerloom_workbook_template.xlsx>`

**Optional CSV-aligned template (download):** :download:`LedgerLoom Workbook CSV-aligned template (XLSX) <../_static/ledgerloom_workbook_template_csv_headers.xlsx>`

Chapter 1 — Transactions (Journal)
----------------------------------

Step 1: Enter transactions as journal entries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In **Journal_Transactions**, record each transaction using:

- Date
- EntryID
- Memo
- Account
- Debit
- Credit

**Check every EntryID balances.**

Quick balance check (spreadsheet idea)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make a small summary table (or pivot) grouped by EntryID:

- TotalDebit = SUM of Debit
- TotalCredit = SUM of Credit
- Difference = TotalDebit - TotalCredit

Every Difference must be 0.

Common beginner mistakes
^^^^^^^^^^^^^^^^^^^^^^^^

- Putting the amount in both Debit and Credit on the same row.
- Misspelling an account name (COA prevents this).
- Forgetting one line of a multi-line entry.

Chapter 2 — Journal → Unadjusted Trial Balance
----------------------------------------------

A trial balance is a list of accounts with their debit/credit balances.

Step 1: Build account totals from the journal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In **TB_Unadjusted**, list every account from the COA.
Then compute totals from the journal.

A simple approach is to compute two totals per account:

- DebitTotal = sum of all journal debits for that account
- CreditTotal = sum of all journal credits for that account

Excel-style formulas (conceptual)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your journal is in a table named ``Journal`` with columns ``Account``, ``Debit``, ``Credit``:

- DebitTotal:  SUMIFS(Journal[Debit],  Journal[Account],  [@Account])
- CreditTotal: SUMIFS(Journal[Credit], Journal[Account],  [@Account])

Then compute the trial balance presentation:

- If DebitTotal > CreditTotal, the account has a Debit balance
- If CreditTotal > DebitTotal, the account has a Credit balance

Step 2: Prove the TB balances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At the bottom:

- TotalDebits = SUM(DebitBalanceColumn)
- TotalCredits = SUM(CreditBalanceColumn)

These must match exactly.

Chapter 3 — Adjusting Entries → Adjusted Trial Balance
------------------------------------------------------

Adjusting entries record accruals and deferrals (they usually happen at period end).

Step 1: Record adjusting entries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In **Journal_Adjustments**, record entries in the same journal format.
Use EntryIDs like A001, A002, etc.

Each adjusting entry must balance.

Step 2: Create TB_Adjusted
^^^^^^^^^^^^^^^^^^^^^^^^^^

In **TB_Adjusted**, start from the unadjusted TB, then apply adjustments.

A clean method:

- Compute AdjustmentDebitTotal per account from Journal_Adjustments
- Compute AdjustmentCreditTotal per account from Journal_Adjustments
- AdjustedDebitTotal  = UnadjustedDebitTotal  + AdjustmentDebitTotal
- AdjustedCreditTotal = UnadjustedCreditTotal + AdjustmentCreditTotal

Then recompute the Debit/Credit balance presentation and re-check totals.

Checkpoint: what changed?
^^^^^^^^^^^^^^^^^^^^^^^^^

At this stage you should be able to answer:

- Which accounts changed due to accrual accounting?
- Why did they change?
- Did any cash account change due to adjustments? (Usually no.)

Chapter 4 — Closing Entries → Post-close Trial Balance
------------------------------------------------------

Closing transfers temporary account balances into equity and resets them to zero.

Temporary vs permanent accounts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Temporary (should go to zero after close):

- Revenue
- Expense
- Dividends/Draws (depending on the course)

Permanent (remain after close):

- Assets
- Liabilities
- Equity accounts (including Retained Earnings)

Step 1: Compute net income (from the adjusted TB)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Net Income = Total Revenues - Total Expenses

(Your spreadsheet may compute this directly from the TB.)

Step 2: Create closing entries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the **Closing** tab, create entries that:

1) Close revenues to Retained Earnings (or Income Summary, depending on course design)
2) Close expenses to Retained Earnings (or Income Summary)
3) Close dividends/draws directly to Retained Earnings (not to income summary)

Important concept
^^^^^^^^^^^^^^^^^

- Revenues normally have **credit** balances.
- Expenses normally have **debit** balances.

So your closing entries will usually:
- Debit revenue accounts to bring them to zero
- Credit expense accounts to bring them to zero
- Move the net amount into equity

Step 3: Build the Post-close TB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create **TB_PostClose** by applying closing entries to the adjusted TB.

The post-close TB should contain **only balance sheet accounts**.

Final invariant check
^^^^^^^^^^^^^^^^^^^^^

- Total Debits = Total Credits
- Revenue / Expense / Dividends-or-Draws accounts should be zero (or absent)

Why this matters before LedgerLoom
----------------------------------

If you can produce these tables in a spreadsheet:

- you understand the accounting cycle,
- you can interpret what LedgerLoom outputs,
- and you can quickly diagnose errors when LedgerLoom flags something.

LedgerLoom is not the answer engine — it’s the verifier.

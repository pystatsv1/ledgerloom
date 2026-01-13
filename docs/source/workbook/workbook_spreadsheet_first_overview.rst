Spreadsheet-First Track (No LedgerLoom Yet)
===========================================

This section teaches you how to complete Workbook Chapters 1–4 using **only a spreadsheet**
(Excel, Google Sheets, or LibreOffice Calc).

**Why do this first?**

LedgerLoom is like a “spelling and grammar checker” for accounting work:
it can catch mistakes and enforce rules, but it should never replace your understanding.
If you can build the accounting cycle in a spreadsheet first, then LedgerLoom becomes easy to interpret.

What you will build in your spreadsheet
---------------------------------------

By the end of this section, you will be able to:

1. Record transactions as **journal entries** (debits and credits).
2. Summarize the journal into an **unadjusted trial balance**.
3. Add **adjusting entries** and produce an **adjusted trial balance**.
4. Create **closing entries** and produce a **post-close trial balance**.

LedgerLoom will later verify these same steps automatically.

Key accounting rules (keep these visible)
-----------------------------------------

**Rule 1 — Debits must equal credits in every entry.**
If an entry is unbalanced, it is not valid double-entry accounting.

**Rule 2 — The trial balance is the “whole book in one table.”**
If your journal is correct, then your trial balance totals will match:
Total Debits = Total Credits.

**Rule 3 — Adjusting entries do not change cash.**
They update accrual-based balances (prepaids, accruals, depreciation, etc.).

**Rule 4 — Closing resets temporary accounts.**
Revenue, expenses, and dividends/draws should be **zero** after closing.
Only balance sheet accounts remain in the post-close trial balance.

Your spreadsheet layout (recommended)
-------------------------------------

**Optional template (download):** :download:`LedgerLoom Workbook spreadsheet template (XLSX) <../_static/ledgerloom_workbook_template.xlsx>`

**Optional CSV-aligned template (download):** :download:`LedgerLoom Workbook CSV-aligned template (XLSX) <../_static/ledgerloom_workbook_template_csv_headers.xlsx>`

See also: :doc:`workbook_check_your_work_pack` (optional completed spreadsheet + reference outputs).
Create a workbook with these tabs:

- **COA** (Chart of Accounts)
- **Journal_Transactions**
- **Journal_Adjustments**
- **Ledger** (optional but helpful)
- **TB_Unadjusted**
- **TB_Adjusted**
- **Closing**
- **TB_PostClose**

You can do this in any spreadsheet software. The goal is clarity, not fancy formatting.

Chart of Accounts (COA) tab
---------------------------

Create a COA table with at least these columns:

- Account
- Type  (Asset / Liability / Equity / Revenue / Expense / Dividends-or-Draws)
- NormalBalance (Debit or Credit)

This COA becomes your “dictionary.” Every journal line must use a valid Account from the COA.

Journal format (Transactions + Adjustments)
-------------------------------------------

Both journal tabs should use the same structure:

- Date
- EntryID  (a unique ID per entry; example: T001, T002, A001...)
- Memo
- Account
- Debit
- Credit

Each entry can have multiple lines, but all lines with the same EntryID must balance:
Sum(Debit) = Sum(Credit).

How this connects to LedgerLoom later
-------------------------------------

LedgerLoom uses CSV templates that mirror this journal structure.
When you later run LedgerLoom, you will:

1) Fill the same journal data (usually in a spreadsheet),
2) Export to CSV, and
3) Run `ledgerloom check` and `ledgerloom build` to verify your work.

In other words: **you do the accounting; LedgerLoom checks it.**

Workbook Onboarding: What is LedgerLoom?
========================================

LedgerLoom is a small tool that helps you **verify** your accounting work.
It is designed to *complement* what you already do in **Excel / Google Sheets**.

If you’ve ever thought:

- “My spreadsheet looks right… but how do I know it really balances?”
- “I got the right final numbers… but I’m not sure I understand why.”
- “One tiny sign mistake could ruin everything and I wouldn’t notice.”

…then LedgerLoom is built for you.

In one sentence
---------------

**QuickBooks records transactions. Excel (or Sheets) models and explains them. LedgerLoom verifies the accounting cycle and produces clean artifacts you can compare and trust.**

(You do *not* need QuickBooks for this workbook. It’s optional.)

Why LedgerLoom exists (the gap it fills)
----------------------------------------

Excel/Sheets is incredibly flexible. You can build journal entries, trial balances,
and statements. But spreadsheets have a weakness:

**they do not automatically enforce accounting invariants**.

That means it’s possible to build a spreadsheet that *looks* correct while having silent problems:

- debits and credits don’t truly balance
- signs are flipped (a common beginner error)
- accounts are missing or mapped incorrectly
- you accidentally “fix” the output without fixing the logic

LedgerLoom is meant to close that gap by treating accounting like a pipeline you can
**run and check**—similar to how software developers “compile” and test code.

Where LedgerLoom fits (Excel/Sheets-first workflow)
---------------------------------------------------

Think of a three-part workflow:

1) **Excel / Sheets is your workbench**
   - You build journal entries, adjustment tables, schedules, and explanations.
   - You learn accounting logic here.

2) **LedgerLoom is your verifier**
   - It ingests your exported tables (CSV files).
   - It checks invariants (e.g., balanced entries).
   - It produces canonical outputs (artifacts) you can compare against your workbook.

3) **(Optional) QuickBooks is the system of record**
   - In real practice, QuickBooks is where transactions live.
   - LedgerLoom can sit between QuickBooks exports and your analysis workbook.

This workbook focuses on steps (1) and (2).

What LedgerLoom does (and does NOT do)
--------------------------------------

LedgerLoom DOES:

- Validate that journal entries are balanced (debits = credits).
- Generate canonical postings and trial balances from your entries.
- Produce consistent “artifact” CSVs you can open in Excel/Sheets.
- Catch common mistakes early (sign errors, missing accounts, mapping slips).
- Produce repeatable outputs: same inputs → same artifacts (great for learning and debugging).

LedgerLoom does NOT:

- Replace Excel/Sheets (you still do the thinking and modeling there).
- Replace QuickBooks or your chart of accounts.
- “Solve accounting problems” for you (it won’t invent FIFO layers or schedules).
- Pick accounting policies—**it verifies invariants** and makes your workflow clearer.

A mental model that helps: “Spreadsheet + verifier”
---------------------------------------------------

In this workbook, you should think:

- Your spreadsheet is like a “draft solution.”
- LedgerLoom is like the “unit tests” for your accounting cycle.
- When LedgerLoom disagrees with your workbook, you learn *where your logic broke*.

This is the key educational idea:

**You learn faster when you can see exactly where your accounting pipeline stopped making sense.**

How the workbook chapters use LedgerLoom
----------------------------------------

Across Chapters 1–4, you’ll build the full accounting cycle in small steps:

- **Chapter 1:** Transactions → Journal entries
- **Chapter 2:** Journal entries → Postings → Unadjusted Trial Balance
- **Chapter 3:** Adjusting entries → Adjusted Trial Balance
- **Chapter 4:** Closing entries → Post-close Trial Balance (Balance Sheet only)

At each stage, you will:

1) enter data / logic in Excel or Sheets
2) export a CSV table (simple files)
3) run LedgerLoom to produce artifacts
4) compare artifacts back to your workbook

What success looks like (your goal)
-----------------------------------

You’re successful when you can say:

- “My workbook is not just a set of numbers—it’s a correct accounting pipeline.”
- “If something is wrong, I know exactly where to look.”
- “I can reproduce the same results any time from the same inputs.”

Next: Student Quick Start
-------------------------

When you’re ready to run LedgerLoom, go to:

:doc:`student_quick_start`


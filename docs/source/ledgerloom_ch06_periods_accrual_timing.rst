Chapter 06: Periods, accrual, and timing
========================================

A modern ledger is an **append-only event log** plus a set of **derived views**.

In Chapter 04 we treated the general ledger like a database: postings are the fact table,
and statements are queries.

This chapter adds one crucial dimension to the database mental model:

**Time.** (a.k.a. the accounting period)

Why periods exist
-----------------
Periodization is a measurement choice:

- We want to describe performance **for a slice of time** (a month, quarter, year).
- But real-world business activity does not arrive neatly “inside the slice.”
  Invoices, bills, and prepayments create *timing gaps*.

Accounting solves this with two different lenses:

Accrual basis
-------------
Accrual basis says:

- recognize **revenue when earned** (often at invoice / delivery),
- recognize **expenses when incurred** (even if paid later).

From a developer perspective, accrual accounting is:

- a rule for mapping events to *which period* they affect,
- plus a pipeline of deterministic derived views that make that mapping auditable.

Cash basis
----------
Cash basis says:

- recognize revenue when **cash is received**,
- recognize expenses when **cash is paid**.

Cash basis is a useful baseline because it is intuitive.
It also helps you *see* why accrual adjustments exist: cash timing can make
a “good month” look bad (or vice versa).

What you will build
-------------------
You will run a tiny 2-month journal (Jan/Feb) that includes timing differences:

- invoice in January, cash collected in February (Accounts Receivable timing)
- utilities incurred in January, paid in February (Accounts Payable timing)
- rent prepaid in January for February (prepaid timing)
- a cash sale + a cash purchase (where cash and accrual match)

Then you will materialize two income statement views by period:

- **Accrual-basis income statement** (derived from Revenue and Expenses postings)
- **Cash-basis income statement** (derived from cash movements, classified as “customer receipts” or “payments”)

Finally, you will generate a cutoff diagnostic table that explains *why* the two differ.

Run it
------
From the repo root::

  make ll-ch06

Or directly::

  python -m ledgerloom.chapters.ch06_periods_accrual_timing --outdir outputs/ledgerloom --seed 123

Artifacts
---------
The runner writes::

  outputs/ledgerloom/ch06/postings.csv
  outputs/ledgerloom/ch06/balances_by_period.csv
  outputs/ledgerloom/ch06/income_statement_accrual_by_period.csv
  outputs/ledgerloom/ch06/income_statement_cash_by_period.csv
  outputs/ledgerloom/ch06/cutoff_diagnostics.csv
  outputs/ledgerloom/ch06/balances_as_of.csv
  outputs/ledgerloom/ch06/invariants.json
  outputs/ledgerloom/ch06/manifest.json

How to read the outputs
-----------------------
**postings.csv**
  The canonical fact table: one row per posting, with derived columns such as
  ``raw_delta`` and ``signed_delta``. (Period is derived downstream by slicing ``date``.)

**balances_by_period.csv**
  A materialized view: signed balances grouped by ``period`` and ``(root, account)``.
  This is the “query result” you can build many reports from.

**income_statement_accrual_by_period.csv**
  Accrual profit by period, computed as::

    Net Income = Revenue - Expenses

  where Revenue and Expenses are derived from postings using normal-balance sign conventions.

**income_statement_cash_by_period.csv**
  Cash profit by period, computed from cash movements classified as:

  - cash revenue: cash increases tied to customer activity (cash sales or collections on receivables)
  - cash expense: cash decreases tied to operating activity (cash purchases, AP payments, prepayments)

**cutoff_diagnostics.csv**
  A per-entry explanation table that shows, for each event, the accrual impact and the cash impact.
  This table is your “period boundary debugger.”

**balances_as_of.csv**
  A tiny “as-of” snapshot for month-end boundaries, showing how timing differences live on the balance sheet:
  receivables, payables, and prepaids are exactly the mechanism by which accrual moves income *without*
  moving cash.

Software engineering takeaways
------------------------------
This chapter is intentionally designed to reinforce an engineering mindset:

- **An immutable log + derived views** is a powerful architecture for correctness.
- Period handling becomes explicit: time is a dimension, not a side effect.
- Deterministic artifacts + golden tests give you confidence to extend the system (Chapter 07 and beyond).
- Diagnostics matter: when something looks “wrong,” you want data structures that explain *why*.

Next
----
Chapter 07 treats adjusting entries as **late-arriving data** with provenance and auditability,
building directly on the cutoff diagnostic patterns introduced here.

# LedgerLoom

LedgerLoom is an opinionated Python project that teaches accounting using modern developer mental models:
**event logs**, **derived views**, **invariants**, and **reproducible pipelines**.

It ships as:

- a Python package (`ledgerloom`) you can run locally
- a ReadTheDocs “textbook” with short chapters + reproducible outputs

## Links

- Docs: https://ledgerloom.readthedocs.io/en/latest/
- PyPI: https://pypi.org/project/ledgerloom/
- GitHub: https://github.com/pystatsv1/ledgerloom

## Quickstart

### Install

```bash
pip install ledgerloom
```

### Run Chapter 01 (Journal vs Event Log)

This chapter generates a small, deterministic demo dataset and writes artifacts to an output folder:

```bash
python -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir outputs/ledgerloom --seed 123
```

### You should see files like

- `journal.csv` — traditional accounting journal
- `eventlog.jsonl` — append-only event log
- `ledger_view.csv` — derived ledger view
- `trial_balance.csv` — invariant check
- `entry_explanations.md` — human-friendly explanation

## Why LedgerLoom exists

Many people learn accounting as rules + vocabulary.

LedgerLoom teaches accounting as **systems engineering**:

- a **ledger** is a *database view* of an **event log**
- **double-entry** is a **consistency invariant**
- a **trial balance** is an automated **check**
- financial statements are **deterministic outputs** from well-defined transformations

**Core idea:**  
> Don’t just calculate results — engineer them.

## The mental model mapping

| Accounting concept | Developer mental model |
|---|---|
| Journal entries | Append-only event log (immutable facts) |
| General ledger | Derived view / projection over events |
| Double-entry | Invariant: debits == credits (by entry) |
| Trial balance | Automated check over account totals |
| Close process | Period-end transformation + roll-forward |
| Audit trail | Reproducibility + provenance + diffs |
| Reconciliation | Control loop: expected vs observed |

---

## Project vision and roadmap

## LedgerLoom Vision Document (v0.1.x)

### One-line summary

LedgerLoom is an MIT-licensed Python library + CLI + ReadTheDocs “textbook” that teaches accounting using modern developer mental models—event logs, database views, invariants, and reproducible pipelines—while also growing into a practical tool for generating trustworthy, explainable financial statements from real-world data.

### 1) What LedgerLoom is

LedgerLoom is a learning-first accounting engine built the way software people naturally think:

- Event log first (append-only records of what happened)
- Views second (trial balance, income statement, balance sheet as derived summaries)
- Invariants always (double-entry balancing, account normal balances, period close rules)
- Reproducible artifacts (deterministic outputs, manifests, memos, tables, figures)
LedgerLoom is intentionally designed to “translate” traditional accounting concepts—journal entry, general ledger, debits/credits, trial balance, closing—into a language that matches modern Python + data workflows, without losing the rigor that makes accounting trustworthy.

Current state (from the codebase):

- RTD docs and PyPI release are live
- A clean project scaffold exists (docs, CI, publishing, CLI)
- Chapter 01 is implemented end-to-end with a script, test, docs page, and a make target
### 2) Value proposition

#### For learners

LedgerLoom reduces the cognitive load of accounting by:

- Reframing debits/credits as an encoding of constraints instead of a mystical rule set
- Showing how statements are “just” summary statistics over a validated event stream
Connecting accounting workflows to things developers already know:

- database tables and views
- event sourcing
- schema + constraints + tests
- reproducible pipelines (like ML/analytics pipelines)
#### For practitioners

LedgerLoom aims to become a practical “accounting pipeline toolkit”:

- ingest common exports (CSV from QuickBooks/Xero/Wave/ERP, bank feeds)
- validate and normalize into an event log
- produce statement-quality reports and audit-friendly artifacts
- support “closing” workflows and documentation templates
- enable analysis (variance, trend, anomaly detection, forecasting) on top of a trusted ledger model
Key differentiator: LedgerLoom doesn’t just compute outputs—it emphasizes engineering trust:

- deterministic results
- explicit assumptions
- testable invariants
- reproducible builds
- clear lineage from transactions → ledger → statements
### 3) Goals and non-goals

#### Primary goals

Best-in-class learning tool for modern software minds:

- teach core accounting ideas without forcing legacy mental models up front
- provide readable chapters, runnable scripts, and test-backed outputs
Practical toolchain for real data:

- utilities for importing, validating, and reporting
- export artifacts to CSV/JSON/HTML/PDF-friendly formats
Open-source excellence:

- contributor-friendly repo
- stable API boundaries
- strong docs
- disciplined releases
#### Non-goals (for now)

Replacing full accounting systems (QuickBooks, Xero, NetSuite)

Real-time multi-user bookkeeping UI

Tax filing, payroll filing, jurisdiction-specific compliance automation

GAAP/IFRS authoritative guidance (LedgerLoom can explain concepts, not act as an official standard)

LedgerLoom should include clear disclaimers: educational + tooling, not professional accounting advice.

### 4) Philosophy: “Accounting as a data system”

LedgerLoom treats accounting as a measurement system with:

- Events (sales, payments, payroll runs, depreciation, inventory movement)
- Classification (chart of accounts)
- Constraints (balance to zero, period boundaries, normal balances)
- Summaries (statements)
- Controls (reconciliations, audit trail, approvals)
This is how developers build reliable systems—and it maps cleanly to:

- event sourcing
- database modeling
- data pipelines
- reproducibility + test suites
### 5) Product shape and repo conventions

LedgerLoom intentionally mirrors the PyStatsV1 “chapter pipeline” approach:

#### “Chapter = code + docs + test + make target”

For each chapter XX, we aim to have:

- docs/source/ledgerloom_chXX_<topic>.rst
- scripts/ledgerloom_chXX_<topic>.py
- tests/test_ledgerloom_chXX_<topic>.py
- Makefile target: ll-chXX
- outputs written to: outputs/ledgerloom/chXX/…
Each chapter should produce:

- a small event log (e.g., JSONL)
- derived views (trial balance, statements)
- at least one chart/table
- a short memo or assumptions log (audit-friendly narrative)
- a manifest describing artifacts
- This keeps the textbook runnable and the outputs trustworthy.
### 6) The LedgerLoom “textbook” plan (RTD)

Below is a proposed chapter outline that builds from “developer mental models” into full accounting workflows. The intent is that each chapter is:

- Conceptual explanation
- Minimal runnable example
- Artifacts + tests
- Exercises
- Bridge section: “How this maps to accounting jargon” and “How this maps to databases / OOP”
#### PART I — Foundations: Accounting for developers

- **Ch 01 — Journal vs Event Log (MVP already)**
  - Journal entry as a structured event
  - Event log as append-only truth
  - Trial balance and statements as derived views
  - The “double-entry invariant” as a constraint
- **Ch 02 — Debits/Credits are an encoding**
  - Why debits/credits exist historically
  - Normal balances and sign conventions
  - A modern representation: signed amounts + constraints
  - “Developer translation table” for common account types
- **Ch 03 — Chart of Accounts as a schema**
  - Accounts as dimensions / classification
  - Parent-child trees and rollups
  - Naming, codes, segments (department/location/project)
  - Designing a chart for analysis (not just bookkeeping)
- **Ch 04 — General Ledger as a database**
  - Ledger tables: entries, postings, accounts
  - Views: balances by account, by period, by segment
  - Indexing concepts and query patterns
  - Immutable event log + derived materialized views
#### PART II — The accounting cycle as a pipeline

- **Ch 05 — The accounting equation as an invariant**
  - A = L + E as a system constraint
  - How every valid event preserves it
  - Detecting corruption: “check equations” and diagnostics
- **Ch 06 — Periods, accrual, and timing**
  - Cash vs accrual from a data perspective
  - Revenue recognition intuition (no standards rabbit hole yet)
  - Cutoffs and period boundaries
  - Why timing drives adjustments
- **Ch 07 — Adjusting entries as “late-arriving data”**
  - Accruals, deferrals, estimates
  - Adjustments as separate events with provenance
  - Audit trail: who/why/when
  - Tests: “post-adjustment trial balance must still balance”
- **Ch 08 — Closing as a controlled transformation**
  - Temporary vs permanent accounts
  - Income summary mechanics
  - Retained earnings flow
  - Closing checklist as a reproducible workflow
#### PART III — Operational subsystems (practical bookkeeping)

- **Ch 09 — Accounts Receivable (AR) lifecycle**
  - Invoices, payments, credits, aging
  - Matching events (invoice → cash receipt)
  - AR subledger vs GL control account
  - Practical import: CSV-based AR events
- **Ch 10 — Accounts Payable (AP) lifecycle**
  - Bills, payments, vendor credits
  - AP aging and cash planning
  - Approvals and controls as metadata
  - Practical import: CSV-based AP events
- **Ch 11 — Inventory and COGS**
  - Perpetual vs periodic
  - Inventory movements as events
  - COGS linkage to sales
  - Practical: simple costing assumptions + limitations
- **Ch 12 — Fixed assets and depreciation**
  - Capitalization vs expense
  - Depreciation schedules as deterministic generators
  - Disposal and impairment concepts
  - Practical: a depreciation engine that emits events monthly
- **Ch 13 — Payroll as a multi-line event**
  - Gross pay, withholdings, employer taxes
  - Payables and remittances
  - Controls: reconciliation to payroll register
  - Practical: import a payroll register export
#### PART IV — Controls, auditability, and “trust engineering”

- **Ch 14 — Reconciliations as quality control**
  - Bank reconciliation as matching problem
  - Variances and investigation workflow
  - How to encode reconciliation status in metadata
- **Ch 15 — Materiality and “inconsequential misstatements”**
  - Why accounting uses thresholds
  - Aggregation risk (“further undetected misstatements”)
  - Practical: rules + tests + reporting of discrepancies
- **Ch 16 — Audit trail, provenance, and explainability**
  - Every output should be explainable back to events
  - Attestations: “why we believe this is correct”
  - Practical: manifests, checksums, run metadata, version stamping
#### PART V — Analytics on top of a trusted ledger

- **Ch 17 — Statement analysis as summary statistics**
  - Trend, common-size statements
  - Ratios as derived metrics
  - How to avoid misleading visuals
- **Ch 18 — Forecasting and planning basics**
  - Driver-based forecasting (revenue, COGS, expenses)
  - Scenario inputs and reproducible assumptions
  - Practical: producing a forecast memo + uncertainty band (later)
#### Appendices (always useful on RTD)

- A. Glossary: Accounting ↔ Developer translation
- B. Data model reference (tables / JSON schemas)
- C. Cookbook: “How do I…?”
import bank CSV

generate a trial balance

close a period

produce statements

- D. Contributing guide for new chapters
- E. Style rules for artifacts + docs (PyStatsV1-style)
### 7) Practical tool roadmap (how it becomes “useful at work”)

LedgerLoom can evolve into a practical toolkit through carefully staged capability:

#### Stage 1: “Local, deterministic ledger engine” (now → v0.3)

stable core model (events/postings)

basic reports (TB/IS/BS)

chapter scripts as canonical examples

strong tests and docs

#### Stage 2: “Import real exports” (v0.3 → v0.6)

CSV import helpers:

- bank transactions
- invoices/payments
- bills/vendor payments
- payroll register
mapping layer:

- user-provided account mapping tables
- validation + reporting of unmapped items
output exports:

- CSV tables
- JSON artifacts
- “audit memo” templates
#### Stage 3: “Database-native mode” (v0.6 → v1.0)

optional SQLite/DuckDB backend

views built as SQL

reproducible pipelines that run end-to-end on real datasets

#### Stage 4: “Learning + practice platform”

sample datasets

exercises with answer keys

optional notebook gallery

“mini projects” (close a month, reconcile a bank account, produce statements)

### 8) How LedgerLoom becomes the best it can be

#### Make it the best learning tool

ruthless clarity: every chapter answers “what problem does this solve?”

translation tables everywhere (jargon ↔ developer terms)

runnable artifacts + tests (students trust what they run)

“why this exists historically” but “how to model it today”

#### Make it the best practical tool

focus on common workflows:

- import → validate → report → memo
embrace imperfect real data:

- missing fields
- inconsistent descriptions
- duplicates
provide strong diagnostics:

- what failed, why, where to fix it
- keep the core small and stable; add importers as plugins/modules
#### Make it the best open-source project

consistent chapter template

issues labeled by chapter and skill level

“good first issue” tasks like:

- add a glossary entry
- add one diagnostic check
- add one small importer
- regular releases with changelogs
- CI always green; docs always build
### 9) Success criteria (how we’ll know it’s working)

#### Learning success

readers can explain:

- what a journal entry is in event-log terms
- why debits/credits work (invariant encoding)
- how statements are produced mechanically
readers can run:

- chapter scripts and reproduce outputs
- tests that confirm invariants
#### Practical success

user can:

- import a simple export (bank CSV)
- map accounts
- produce a trial balance and statements
- reconcile and flag mismatches
- generate an “explainable output pack”
#### Community success

contributors can add a chapter without guessing:

- template and conventions are obvious
- tests are easy to write
- docs wiring is predictable
### 10) Near-term development plan (next 3 releases)

#### v0.1.x (now)

Ch01 done; polish docs and README

add badges, link RTD/PyPI, add “Quickstart” section with commands

ensure CLI UX is clean and stable

#### v0.2.0

Chapter 02: Debits/Credits as encoding

include a “signed amount” representation alongside classic D/C

add invariant tests and a small diagnostic report

#### v0.3.0

Chapter 03: Chart of accounts as schema

introduce segments (department/project) as metadata

add rollups and a “statement by segment” example

---

## Contributing

LedgerLoom is MIT-licensed and welcomes contributions.

If you’d like to help, a great starting point is:

- improve docs clarity (translation tables, worked examples)
- add small diagnostics / invariant checks
- help implement the next chapter(s) in the roadmap (code + docs + tests)

See the GitHub repo for issues and contribution guidelines.

## Disclaimer

LedgerLoom is educational software and tooling. It is **not** professional accounting advice and is **not** a replacement for a full accounting system (e.g., QuickBooks/Xero) or jurisdiction-specific compliance guidance.

---

## Appendix: Original README draft (verbatim)

<details>
<summary>Click to expand</summary>

````markdown
# LedgerLoom

LedgerLoom is a tiny, opinionated Python project that teaches accounting using modern developer mental models:
**event logs**, **derived views**, and **invariants**.

It ships as:

- a Python package (`ledgerloom`) you can run locally
- a ReadTheDocs “textbook” with short chapters + reproducible outputs

## Install

```bash
pip install ledgerloom


## Run Chapter 01 (Journal vs Event Log)

This chapter generates a small, deterministic demo dataset and writes artifacts to an output folder:

```bash
python -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir outputs/ledgerloom --seed 123
```

## You should see files like:

**journal.csv (traditional accounting journal)**

**eventlog.jsonl (append-only event log)**

**ledger_view.csv (derived view)**

**trial_balance.csv (invariant check)**

**entry_explanations.md (human-friendly explanation)**


# LedgerLoom

**LedgerLoom** teaches accounting using modern developer mental models: **event logs**, **database views**, **invariants**, and **reproducible pipelines**.

It is both:
1) a **textbook-style** set of chapters on Read the Docs, and  
2) a **tiny, MIT-licensed Python library + CLI** for generating and validating accounting-shaped artifacts.

---

## Links

- Docs: https://ledgerloom.readthedocs.io/en/latest/
- PyPI: https://pypi.org/project/ledgerloom/
- GitHub: https://github.com/pystatsv1/ledgerloom

---

## Why LedgerLoom exists

Many people learn accounting as rules + vocabulary.

LedgerLoom teaches accounting as **systems engineering**:

- a **ledger** is a *database view* of an **event log**
- **double-entry** is a **consistency invariant**
- a **trial balance** is an automated **check**
- financial statements are **deterministic outputs** from well-defined transformations

**Core idea:**  
> Don’t just calculate results — engineer them.

---

## The mental model mapping

| Accounting concept | Developer mental model |
|---|---|
| Journal entries | Append-only event log (immutable facts) |
| General ledger | Derived view / projection over events |
| Double-entry | Invariant: debits == credits (by entry) |
| Trial balance | Automated check over account totals |
| Close process | Period-end transformation + roll-forward |
| Audit trail | Reproducibility + provenance + diffs |
| Reconciliation | Control loop: expected vs observed |

---

## Install

```bash
pip install ledgerloom
````

</details>

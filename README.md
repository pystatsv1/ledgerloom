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

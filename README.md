# LedgerLoom

**LedgerLoom** teaches accounting using modern developer mental models: **event logs**, **database views**, **invariants**, and **reproducible pipelines**.

It is both:
1) a **textbook-style** set of chapters on Read the Docs, and  
2) a **tiny, MIT-licensed Python library + CLI** for generating and validating accounting-shaped artifacts.

---

## Badges

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

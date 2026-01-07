"""LedgerLoom Chapter 04 — General Ledger as a database.

This chapter takes a small (but realistic) double-entry journal and treats it as a
mini database:

- Fact table: postings (one row per debit/credit line)
- Dimensions: account (and a simple department segment)
- Views / materialized views: balances by account, by period, by segment
- Constraints: enforce invariants (double-entry, recognized roots, etc.)

Run:

    python -m ledgerloom.chapters.ch04_general_ledger_database --outdir outputs/ledgerloom --seed 123

Artifacts land under:

    outputs/ledgerloom/ch04/

Designed to be deterministic across platforms (LF line endings).
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path


from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine
from ledgerloom.artifacts import manifest_items, write_csv_df, write_json, write_text
from ledgerloom.trust.pipeline import emit_trust_artifacts


# Chapter-owned I/O helpers are centralized in ledgerloom.artifacts.


# -------------------------
# Sample data (journal)
# -------------------------


def _sample_entries(seed: int) -> list[Entry]:
    """A tiny journal spanning two months and two departments.

    Seed is accepted for API symmetry with other chapters, but the core dataset is
    intentionally stable so golden-file determinism is maximally robust.
    """

    def e(
        entry_id: str,
        dt: date,
        narration: str,
        dept: str,
        postings: list[tuple[str, str, str]],
    ) -> Entry:
        ps: list[Posting] = []
        for acct, dr, cr in postings:
            ps.append(Posting(account=acct, debit=Decimal(dr), credit=Decimal(cr)))
        return Entry(dt=dt, narration=narration, postings=ps, meta={"entry_id": entry_id, "department": dept, "seed": seed})

    return [
        e(
            "E0001",
            date(2025, 1, 2),
            "Owner contribution to start the month",
            "ADM",
            [
                ("Assets:Cash", "5000.00", "0"),
                ("Equity:OwnerCapital", "0", "5000.00"),
            ],
        ),
        e(
            "E0002",
            date(2025, 1, 5),
            "Buy initial inventory on account",
            "OPS",
            [
                ("Assets:Inventory", "1200.00", "0"),
                ("Liabilities:AccountsPayable", "0", "1200.00"),
            ],
        ),
        e(
            "E0003",
            date(2025, 1, 9),
            "Make a cash sale",
            "OPS",
            [
                ("Assets:Cash", "850.00", "0"),
                ("Revenue:Sales", "0", "850.00"),
            ],
        ),
        e(
            "E0004",
            date(2025, 1, 10),
            "Make a credit sale (A/R)",
            "OPS",
            [
                ("Assets:AccountsReceivable", "420.00", "0"),
                ("Revenue:Sales", "0", "420.00"),
            ],
        ),
        e(
            "E0005",
            date(2025, 1, 18),
            "Collect on receivable",
            "OPS",
            [
                ("Assets:Cash", "420.00", "0"),
                ("Assets:AccountsReceivable", "0", "420.00"),
            ],
        ),
        e(
            "E0006",
            date(2025, 1, 28),
            "Pay supplier (A/P)",
            "OPS",
            [
                ("Liabilities:AccountsPayable", "1200.00", "0"),
                ("Assets:Cash", "0", "1200.00"),
            ],
        ),
        e(
            "E0007",
            date(2025, 2, 1),
            "Pay monthly rent",
            "ADM",
            [
                ("Expenses:Rent", "900.00", "0"),
                ("Assets:Cash", "0", "900.00"),
            ],
        ),
        e(
            "E0008",
            date(2025, 2, 6),
            "Payroll for operations",
            "OPS",
            [
                ("Expenses:Wages", "1400.00", "0"),
                ("Assets:Cash", "0", "1400.00"),
            ],
        ),
        e(
            "E0009",
            date(2025, 2, 13),
            "Buy a laptop for admin (project: onboarding)",
            "ADM",
            [
                ("Assets:Equipment", "800.00", "0"),
                ("Assets:Cash", "0", "800.00"),
            ],
        ),
        e(
            "E0010",
            date(2025, 2, 20),
            "Recognize monthly depreciation",
            "ADM",
            [
                ("Expenses:Depreciation", "20.00", "0"),
                ("Assets:AccumulatedDepreciation", "0", "20.00"),
            ],
        ),
    ]


# -------------------------
# Metadata / docs artifacts
# -------------------------


def _query_patterns_md() -> str:
    return """# Chapter 04 — SQL mental model (query patterns)

In this chapter, we treat the **general ledger** like a tiny database.

## Fact table

Think of `postings.csv` as your main fact table.

- One row per posting line.
- The `posting_id` is a stable primary key (`entry_id:line_no`).
- `account` is a dimension (and `root` is a derived classification).
- `department` is a simple segment dimension.

## View 1 — balances by account

**SQL mental model**:

```sql
SELECT
  root,
  account,
  SUM(debit)  AS debit_total,
  SUM(credit) AS credit_total,
  SUM(signed_delta) AS balance
FROM postings
GROUP BY root, account
ORDER BY root, account;
```

## View 2 — balances by month

```sql
SELECT
  SUBSTR(date, 1, 7) AS period,
  root,
  account,
  SUM(signed_delta) AS balance
FROM postings
GROUP BY period, root, account
ORDER BY period, root, account;
```

## View 3 — balances by segment (department)

```sql
SELECT
  department,
  root,
  SUM(signed_delta) AS balance
FROM postings
GROUP BY department, root
ORDER BY department, root;
```

## Running balances (window functions)

```sql
SELECT
  posting_id,
  date,
  account,
  signed_delta,
  SUM(signed_delta) OVER (
    PARTITION BY account
    ORDER BY date, posting_id
  ) AS running_balance
FROM postings
ORDER BY account, date, posting_id;
```

These are the same operations you use in pandas:

- `groupby(...).sum()` for `GROUP BY`
- `groupby(...).cumsum()` for windowed running totals
"""


def _lineage_mermaid() -> str:
    return """```mermaid
flowchart TD
  A[Sample Journal Entries] --> B[postings.csv\n(Fact table)]
  B --> C[balances_by_account.csv\n(Materialized view)]
  B --> D[balances_by_period.csv\n(Materialized view)]
  B --> E[balances_by_department.csv\n(Materialized view)]
  B --> F[running_balance_by_posting.csv\n(Window function)]
  B --> G[invariants.json\n(Constraints)]
  C --> H[manifest.json]
  D --> H
  E --> H
  F --> H
  G --> H
```\n"""


def _manifest_payload(outdir: Path) -> dict[str, object]:
    """Return the manifest payload (deterministic, excludes manifest itself)."""

    files = [p for p in sorted(outdir.glob("*")) if p.is_file() and p.name != "manifest.json"]
    items = manifest_items(outdir, files, name_key="file")
    return {"artifacts": items}


# -------------------------
# Runner
# -------------------------


def _resolve_outdir(outdir: Path) -> Path:
    return outdir / "ch04"


def run(outdir: Path, seed: int) -> Path:
    out = _resolve_outdir(outdir)
    out.mkdir(parents=True, exist_ok=True)

    entries = _sample_entries(seed=seed)

    engine = LedgerEngine()
    postings = engine.postings_fact_table(entries)

    # Views / materializations
    bal_acct = engine.balances_by_account(postings)
    bal_period = engine.balances_by_period(postings)
    bal_dept = engine.balances_by_department(postings)
    running = engine.running_balance_by_posting(postings)

    checks = engine.invariants(entries, postings)

    # Write artifacts
    write_csv_df(out / "postings.csv", postings)
    write_csv_df(out / "balances_by_account.csv", bal_acct)
    write_csv_df(out / "balances_by_period.csv", bal_period)
    write_csv_df(out / "balances_by_department.csv", bal_dept)
    write_csv_df(out / "running_balance_by_posting.csv", running)

    write_json(out / "invariants.json", checks)
    write_json(out / "gl_schema.json", engine.gl_schema_description())

    write_text(out / "sql_mental_model.md", _query_patterns_md())
    write_text(out / "lineage.mmd", _lineage_mermaid())

    run_meta = {
        "chapter": "04",
        "runner": "ledgerloom.chapters.ch04_general_ledger_database",
        "seed": seed,
        "entries": len(entries),
        "postings": int(len(postings)),
    }
    emit_trust_artifacts(out, run_meta=run_meta, manifest=_manifest_payload)

    return out


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LedgerLoom Ch04: general ledger as a database")
    p.add_argument("--outdir", type=Path, default=Path("outputs/ledgerloom"))
    p.add_argument("--seed", type=int, default=123)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    ns = _parse_args(argv)
    out = run(ns.outdir, ns.seed)
    print(f"Wrote LedgerLoom Chapter 04 artifacts -> {out}")


if __name__ == "__main__":
    main()

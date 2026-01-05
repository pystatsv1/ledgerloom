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
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ledgerloom.core import Entry, Posting


# -------------------------
# Money + CSV/JSON helpers
# -------------------------

_CENT = Decimal("0.01")


def _to_cents(x: Decimal) -> int:
    q = x.quantize(_CENT)
    return int(q * 100)


def _cents_to_str(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    dollars = cents // 100
    rem = cents % 100
    return f"{sign}{dollars}.{rem:02d}"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, obj: Any) -> None:
    _write_text(path, json.dumps(obj, indent=2, sort_keys=True))


def _write_df_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# -------------------------
# Domain conventions
# -------------------------

_DEBIT_NORMAL_ROOTS = {"Assets", "Expenses"}
_CREDIT_NORMAL_ROOTS = {"Liabilities", "Equity", "Revenue"}


def _account_root(account: str) -> str:
    return account.split(":", 1)[0]

def _entry_id(entry: Entry) -> str:
    """Stable identifier for an entry (stored in entry.meta)."""
    v = entry.meta.get("entry_id")
    return str(v) if v is not None else ""


def _entry_department(entry: Entry) -> str:
    """A simple segment value used for grouping (stored in entry.meta)."""
    v = entry.meta.get("department")
    return str(v) if v is not None else ""



def _signed_cents(root: str, debit_cents: int, credit_cents: int) -> int:
    """Return balance delta in the account's *normal* sign convention."""

    if root in _DEBIT_NORMAL_ROOTS:
        return debit_cents - credit_cents
    if root in _CREDIT_NORMAL_ROOTS:
        return credit_cents - debit_cents
    # Unknown root: treat like debit-normal, but we also flag this in checks.
    return debit_cents - credit_cents


# -------------------------
# Sample data (journal)
# -------------------------


def _sample_entries(seed: int) -> list[Entry]:
    """A tiny journal spanning two months and two departments.

    Seed is accepted for API symmetry with other chapters, but the core dataset is
    intentionally stable so golden-file determinism is maximally robust.
    """

    # A tiny, understandable chart-of-accounts expressed as colon-path strings.
    # Roots: Assets/Liabilities/Equity/Revenue/Expenses.

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
# Transformations ("tables")
# -------------------------


def _postings_fact_table(entries: list[Entry]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for e in entries:
        dept = (e.meta or {}).get("department", "")
        for i, p in enumerate(e.postings, start=1):
            root = _account_root(p.account)
            dr_c = _to_cents(p.debit)
            cr_c = _to_cents(p.credit)
            rows.append(
                {
                    "posting_id": f"{_entry_id(e)}:{i:02d}",
                    "entry_id": _entry_id(e),
                    "line_no": i,
                    "date": e.dt.isoformat(),
                    "department": dept,
                    "narration": e.narration,
                    "account": p.account,
                    "root": root,
                    "debit": _cents_to_str(dr_c),
                    "credit": _cents_to_str(cr_c),
                    "raw_delta": _cents_to_str(dr_c - cr_c),
                    "signed_delta": _cents_to_str(_signed_cents(root, dr_c, cr_c)),
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["date", "entry_id", "line_no"], kind="mergesort").reset_index(drop=True)
    return df


def _balances_by_account(postings: pd.DataFrame) -> pd.DataFrame:
    # Compute sums as integer cents for stability.
    tmp = postings.copy()
    for col in ["debit", "credit", "raw_delta", "signed_delta"]:
        tmp[f"{col}_cents"] = tmp[col].map(lambda s: int(Decimal(s) * 100))

    g = tmp.groupby(["root", "account"], sort=True, as_index=False).agg(
        debit_cents=("debit_cents", "sum"),
        credit_cents=("credit_cents", "sum"),
        signed_cents=("signed_delta_cents", "sum"),
    )

    def normal_side(root: str) -> str:
        if root in _DEBIT_NORMAL_ROOTS:
            return "debit"
        if root in _CREDIT_NORMAL_ROOTS:
            return "credit"
        return "unknown"

    g["normal_side"] = g["root"].map(normal_side)
    g["debit_total"] = g["debit_cents"].map(_cents_to_str)
    g["credit_total"] = g["credit_cents"].map(_cents_to_str)
    g["balance"] = g["signed_cents"].map(_cents_to_str)

    out = g[["root", "account", "normal_side", "debit_total", "credit_total", "balance"]]
    out = out.sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def _balances_by_period(postings: pd.DataFrame) -> pd.DataFrame:
    tmp = postings.copy()
    tmp["period"] = tmp["date"].str.slice(0, 7)  # YYYY-MM
    tmp["signed_cents"] = tmp["signed_delta"].map(lambda s: int(Decimal(s) * 100))

    g = tmp.groupby(["period", "root", "account"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(_cents_to_str)
    out = g[["period", "root", "account", "balance"]]
    out = out.sort_values(["period", "root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def _balances_by_department(postings: pd.DataFrame) -> pd.DataFrame:
    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(lambda s: int(Decimal(s) * 100))

    g = tmp.groupby(["department", "root"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(_cents_to_str)
    out = g[["department", "root", "balance"]]
    out = out.sort_values(["department", "root"], kind="mergesort").reset_index(drop=True)
    return out


def _running_balance_by_posting(postings: pd.DataFrame) -> pd.DataFrame:
    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(lambda s: int(Decimal(s) * 100))

    tmp = tmp.sort_values(["account", "date", "entry_id", "line_no"], kind="mergesort").reset_index(drop=True)
    tmp["running_balance_cents"] = tmp.groupby("account", sort=True)["signed_cents"].cumsum()
    tmp["running_balance"] = tmp["running_balance_cents"].map(_cents_to_str)

    out = tmp[
        [
            "posting_id",
            "date",
            "account",
            "signed_delta",
            "running_balance",
            "department",
            "narration",
        ]
    ]
    out = out.sort_values(["account", "date", "posting_id"], kind="mergesort").reset_index(drop=True)
    return out


# -------------------------
# Constraints / checks
# -------------------------


def _run_checks(entries: list[Entry], postings: pd.DataFrame) -> dict[str, Any]:
    # Entry-level double-entry invariant.
    entry_rows = []
    for e in entries:
        dr = sum((_to_cents(p.debit) for p in e.postings), 0)
        cr = sum((_to_cents(p.credit) for p in e.postings), 0)
        entry_rows.append({"entry_id": _entry_id(e), "debits": dr, "credits": cr, "ok": dr == cr})

    entry_ok = all(r["ok"] for r in entry_rows)

    # Ledger-level invariant: total (debit - credit) across all postings is 0.
    raw_total_cents = int(sum(Decimal(x) for x in postings["raw_delta"]) * 100)

    # Root validity.
    roots = sorted(set(postings["root"].tolist()))
    recognized_roots = sorted(_DEBIT_NORMAL_ROOTS | _CREDIT_NORMAL_ROOTS)
    unknown_roots = sorted(set(roots) - set(recognized_roots))

    # Primary key uniqueness.
    posting_id_unique = postings["posting_id"].is_unique

    return {
        "entry_double_entry_ok": entry_ok,
        "entry_double_entry_failures": [r for r in entry_rows if not r["ok"]],
        "ledger_raw_delta_zero": raw_total_cents == 0,
        "ledger_raw_delta_total": _cents_to_str(raw_total_cents),
        "posting_id_unique": posting_id_unique,
        "roots_seen": roots,
        "unknown_roots": unknown_roots,
        "notes": [
            "Raw delta uses (debit-credit). It must sum to 0 for a balanced ledger.",
            "Signed delta uses a normal-balance convention by root (Assets/Expenses debit-normal; Liabilities/Equity/Revenue credit-normal).",
        ],
    }


# -------------------------
# Metadata / docs artifacts
# -------------------------


def _schema_description() -> dict[str, Any]:
    return {
        "tables": {
            "postings": {
                "description": "Fact table: one row per posting line (debit or credit).",
                "primary_key": ["posting_id"],
                "columns": [
                    {"name": "posting_id", "type": "string", "example": "E0001:01"},
                    {"name": "entry_id", "type": "string"},
                    {"name": "line_no", "type": "int"},
                    {"name": "date", "type": "date (YYYY-MM-DD)"},
                    {"name": "department", "type": "string"},
                    {"name": "narration", "type": "string"},
                    {"name": "account", "type": "string"},
                    {"name": "root", "type": "string"},
                    {"name": "debit", "type": "decimal (string)"},
                    {"name": "credit", "type": "decimal (string)"},
                    {"name": "raw_delta", "type": "decimal (string)", "meaning": "debit - credit"},
                    {
                        "name": "signed_delta",
                        "type": "decimal (string)",
                        "meaning": "delta in the account's normal-balance convention",
                    },
                ],
                "index_suggestions": [
                    ["date"],
                    ["account", "date"],
                    ["department", "date"],
                ],
            },
            "balances_by_account": {
                "description": "Materialized view: balances grouped by account.",
                "primary_key": ["account"],
            },
            "balances_by_period": {
                "description": "Materialized view: balances grouped by period (YYYY-MM) and account.",
                "primary_key": ["period", "account"],
            },
            "balances_by_department": {
                "description": "Materialized view: balances grouped by department and root.",
                "primary_key": ["department", "root"],
            },
        }
    }


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


def _write_manifest(outdir: Path) -> None:
    items = []
    for p in sorted(outdir.glob("*")):
        if p.is_dir():
            continue
        b = p.read_bytes()
        items.append({"file": p.name, "bytes": len(b), "sha256": _sha256_bytes(b)})
    _write_json(outdir / "manifest.json", {"artifacts": items})


# -------------------------
# Runner
# -------------------------


def _resolve_outdir(outdir: Path) -> Path:
    return outdir / "ch04"


def run(outdir: Path, seed: int) -> Path:
    out = _resolve_outdir(outdir)
    out.mkdir(parents=True, exist_ok=True)

    entries = _sample_entries(seed=seed)
    postings = _postings_fact_table(entries)

    # Views / materializations
    bal_acct = _balances_by_account(postings)
    bal_period = _balances_by_period(postings)
    bal_dept = _balances_by_department(postings)
    running = _running_balance_by_posting(postings)

    checks = _run_checks(entries, postings)

    # Write artifacts
    _write_df_csv(out / "postings.csv", postings)
    _write_df_csv(out / "balances_by_account.csv", bal_acct)
    _write_df_csv(out / "balances_by_period.csv", bal_period)
    _write_df_csv(out / "balances_by_department.csv", bal_dept)
    _write_df_csv(out / "running_balance_by_posting.csv", running)

    _write_json(out / "invariants.json", checks)
    _write_json(out / "gl_schema.json", _schema_description())

    _write_text(out / "sql_mental_model.md", _query_patterns_md())
    _write_text(out / "lineage.mmd", _lineage_mermaid())

    run_meta = {
        "chapter": "04",
        "runner": "ledgerloom.chapters.ch04_general_ledger_database",
        "seed": seed,
        "entries": len(entries),
        "postings": int(len(postings)),
    }
    _write_json(out / "run_meta.json", run_meta)

    _write_manifest(out)

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

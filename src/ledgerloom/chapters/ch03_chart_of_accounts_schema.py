"""LedgerLoom — Chapter 03 (Alt): Chart of Accounts as Schema.

Why an "alternate Chapter 03"?
------------------------------
LedgerLoom is evolving quickly. We keep both early "Chapter 03" threads for now:

- ch03_posting_to_ledger: takes a journal and produces ledger + trial balance
- ch03_chart_of_accounts_schema: defines the COA as a *schema* with metadata

This module implements the COA-as-schema chapter.

Goals
-----
- Treat the chart of accounts (COA) as a *schema* (metadata + constraints)
- Build an "account master" table suitable for joins, validation, and tooling
- Introduce segments (department/project) as schema metadata
- Produce deterministic, inspectable artifacts + golden-file tests

Outputs
-------
Written under: outputs/ledgerloom/ch03AccountsSchema

Core:
- coa_schema.json
- account_master.csv
- segment_dimensions.csv
- segment_values.csv
- income_statement_by_department.csv  (tiny worked example)

Wow / dev artifacts:
- checks.md
- tables.md
- diagnostics.md
- lineage.mmd
- manifest.json
- run_meta.json
- summary.md

Run
---
  python -m ledgerloom.chapters.ch03_chart_of_accounts_schema --outdir outputs/ledgerloom --seed 123
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Sequence

getcontext().prec = 28
D0 = Decimal("0")


def _d(x: str | int | Decimal) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _dec_str(x: Decimal) -> str:
    # Stable money-like formatting (2 decimals), normalize -0.00 -> 0.00
    q = x.quantize(Decimal("0.01"))
    if q == D0:
        return "0.00"
    s = format(q, "f")
    if "." not in s:
        return f"{s}.00"
    whole, frac = s.split(".", 1)
    frac = (frac + "00")[:2]
    return f"{whole}.{frac}"


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, s: str) -> None:
    path.write_text(s, encoding="utf-8", newline="\n")


def write_json(path: Path, obj: object) -> None:
    write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: Sequence[dict[str, str]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def md_table(rows: Sequence[dict[str, str]], cols: Sequence[str], max_rows: int = 10) -> str:
    head = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |\n"
    body = []
    for r in rows[:max_rows]:
        body.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return head + sep + "\n".join(body) + ("\n" if body else "")


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    account_type: str  # asset/liability/equity/revenue/expense
    normal_side: str   # debit/credit
    statement: str     # BS or IS
    rollup_code: str   # parent / rollup bucket
    is_contra: bool
    is_active: bool
    track_department: bool
    track_project: bool
    description: str


@dataclass(frozen=True)
class SegmentValue:
    dimension_code: str  # DEPT or PROJ
    value_code: str
    value_name: str


def default_accounts() -> list[Account]:
    # A tiny but realistic COA with rollups and segment flags.
    # Codes are strings to preserve leading zeros in future expansions.
    return [
        # Rollups (top-level)
        Account("1000", "Assets", "asset", "debit", "BS", "", False, True, False, False, "Rollup: all assets"),
        Account("2000", "Liabilities", "liability", "credit", "BS", "", False, True, False, False, "Rollup: all liabilities"),
        Account("3000", "Equity", "equity", "credit", "BS", "", False, True, False, False, "Rollup: all equity"),
        Account("4000", "Revenue", "revenue", "credit", "IS", "", False, True, True, True, "Rollup: all revenue"),
        Account("5000", "Expenses", "expense", "debit", "IS", "", False, True, True, True, "Rollup: all expenses"),

        # Asset detail
        Account("1100", "Cash", "asset", "debit", "BS", "1000", False, True, False, False, "Cash on hand / bank"),
        Account("1200", "Accounts Receivable", "asset", "debit", "BS", "1000", False, True, True, True, "Customer receivables (segment-tracked)"),
        Account("1300", "Inventory", "asset", "debit", "BS", "1000", False, True, True, True, "Inventory held for sale (segment-tracked)"),
        Account("1500", "Equipment", "asset", "debit", "BS", "1000", False, True, False, True, "Equipment (project-tracked)"),

        # Liability detail
        Account("2100", "Accounts Payable", "liability", "credit", "BS", "2000", False, True, True, True, "Supplier payables (segment-tracked)"),
        Account("2200", "Notes Payable", "liability", "credit", "BS", "2000", False, True, False, True, "Debt instruments (project-tracked)"),

        # Equity detail
        Account("3100", "Owner Capital", "equity", "credit", "BS", "3000", False, True, False, False, "Owner contributions"),
        Account("3200", "Retained Earnings", "equity", "credit", "BS", "3000", False, True, False, False, "Cumulative profits"),

        # Revenue detail (segment tracked)
        Account("4100", "Sales Revenue", "revenue", "credit", "IS", "4000", False, True, True, True, "Product/service revenue"),
        Account("4200", "Service Revenue", "revenue", "credit", "IS", "4000", False, True, True, True, "Services revenue"),

        # Expense detail (segment tracked)
        Account("5100", "COGS", "expense", "debit", "IS", "5000", False, True, True, True, "Cost of goods sold"),
        Account("5200", "Rent Expense", "expense", "debit", "IS", "5000", False, True, True, False, "Rent (dept-tracked)"),
        Account("5300", "Wages Expense", "expense", "debit", "IS", "5000", False, True, True, False, "Wages (dept-tracked)"),
        Account("5400", "Marketing Expense", "expense", "debit", "IS", "5000", False, True, True, True, "Marketing (segment-tracked)"),

        # Contra example
        Account("1510", "Accumulated Depreciation", "asset", "credit", "BS", "1000", True, True, False, True, "Contra-asset for equipment"),
    ]


def default_segments() -> tuple[list[dict[str, str]], list[SegmentValue]]:
    dims = [
        {
            "dimension_code": "DEPT",
            "dimension_name": "Department",
            "required": "false",
            "description": "Operational department (e.g., SALES, OPS).",
        },
        {
            "dimension_code": "PROJ",
            "dimension_name": "Project",
            "required": "false",
            "description": "Project / job / initiative (e.g., P001).",
        },
    ]
    values = [
        SegmentValue("DEPT", "SALES", "Sales"),
        SegmentValue("DEPT", "OPS", "Operations"),
        SegmentValue("PROJ", "P001", "Website Revamp"),
        SegmentValue("PROJ", "P002", "New Product Launch"),
    ]
    return dims, values


def schema_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "account_master": {
            "primary_key": ["code"],
            "fields": [
                {"name": "code", "type": "string", "pattern": r"^\d{4}$", "description": "Account code (4 digits)"},
                {"name": "name", "type": "string"},
                {"name": "account_type", "type": "enum", "values": ["asset", "liability", "equity", "revenue", "expense"]},
                {"name": "normal_side", "type": "enum", "values": ["debit", "credit"]},
                {"name": "statement", "type": "enum", "values": ["BS", "IS"], "description": "Balance Sheet / Income Statement"},
                {"name": "rollup_code", "type": "string", "nullable": True, "description": "Parent rollup bucket"},
                {"name": "is_contra", "type": "bool", "description": "Contra accounts invert the normal balance for presentation"},
                {"name": "is_active", "type": "bool"},
                {"name": "track_department", "type": "bool"},
                {"name": "track_project", "type": "bool"},
                {"name": "description", "type": "string"},
            ],
            "constraints": [
                "unique(code)",
                "rollup_code must reference an existing account or be empty",
                "no cycles in rollup relationships",
                "normal_side is debit for assets/expenses and credit for liabilities/equity/revenue (except contra accounts may differ)",
            ],
        },
        "segments": {
            "dimensions": [
                {"dimension_code": "DEPT", "description": "Department"},
                {"dimension_code": "PROJ", "description": "Project"},
            ],
            "rules": [
                "When an account has track_department=true, postings should include a DEPT value.",
                "When an account has track_project=true, postings should include a PROJ value.",
            ],
        },
    }


def validate_accounts(accounts: Sequence[Account]) -> list[str]:
    checks: list[str] = []

    # unique codes
    codes = [a.code for a in accounts]
    if len(set(codes)) != len(codes):
        checks.append("FAIL: unique_codes — duplicate account codes found")
    else:
        checks.append("PASS: unique_codes — all account codes are unique")

    # rollup references
    code_set = set(codes)
    bad_rollups = [a for a in accounts if a.rollup_code and a.rollup_code not in code_set]
    if bad_rollups:
        checks.append("FAIL: rollup_references — some rollup_code values do not exist")
        for a in bad_rollups[:10]:
            checks.append(f"  - {a.code} rollup_code={a.rollup_code}")
    else:
        checks.append("PASS: rollup_references — all rollup_code values reference an existing account (or empty)")

    # cycle check (child -> parent)
    parent = {a.code: a.rollup_code for a in accounts}

    def has_cycle(start: str) -> bool:
        seen = set()
        cur = start
        while cur and cur in parent:
            if cur in seen:
                return True
            seen.add(cur)
            cur = parent[cur]
        return False

    cycles = [c for c in codes if has_cycle(c)]
    if cycles:
        checks.append("FAIL: rollup_cycles — cycle(s) detected in rollup graph")
        for c in cycles[:10]:
            checks.append(f"  - {c}")
    else:
        checks.append("PASS: rollup_cycles — no cycles detected in rollup relationships")

    # normal side conventions (allow contra exceptions)
    def expected_side(acct_type: str) -> str:
        if acct_type in {"asset", "expense"}:
            return "debit"
        return "credit"

    bad_side = []
    for a in accounts:
        exp = expected_side(a.account_type)
        if (not a.is_contra) and a.normal_side != exp:
            bad_side.append((a.code, a.account_type, a.normal_side, exp))
    if bad_side:
        checks.append("FAIL: normal_side_convention — non-contra accounts violating normal side convention")
        for c, t, ns, exp in bad_side[:10]:
            checks.append(f"  - {c}: type={t} normal_side={ns} expected={exp}")
    else:
        checks.append("PASS: normal_side_convention — normal sides match type conventions (non-contra)")

    # statement mapping
    def expected_stmt(acct_type: str) -> str:
        return "BS" if acct_type in {"asset", "liability", "equity"} else "IS"

    bad_stmt = []
    for a in accounts:
        exp = expected_stmt(a.account_type)
        if a.statement != exp:
            bad_stmt.append((a.code, a.account_type, a.statement, exp))
    if bad_stmt:
        checks.append("FAIL: statement_mapping — accounts mapped to wrong statement")
        for c, t, s, exp in bad_stmt[:10]:
            checks.append(f"  - {c}: type={t} statement={s} expected={exp}")
    else:
        checks.append("PASS: statement_mapping — statement mapping consistent with account types")

    return checks


def build_account_master_rows(accounts: Sequence[Account]) -> list[dict[str, str]]:
    rows = []
    for a in sorted(accounts, key=lambda x: x.code):
        rows.append(
            {
                "code": a.code,
                "name": a.name,
                "account_type": a.account_type,
                "normal_side": a.normal_side,
                "statement": a.statement,
                "rollup_code": a.rollup_code,
                "is_contra": "true" if a.is_contra else "false",
                "is_active": "true" if a.is_active else "false",
                "track_department": "true" if a.track_department else "false",
                "track_project": "true" if a.track_project else "false",
                "description": a.description,
            }
        )
    return rows


def canonical_master_hash(master_rows: Sequence[dict[str, str]]) -> str:
    # stable hash over selected columns
    cols = [
        "code",
        "name",
        "account_type",
        "normal_side",
        "statement",
        "rollup_code",
        "is_contra",
        "is_active",
        "track_department",
        "track_project",
        "description",
    ]
    lines = []
    for r in master_rows:
        lines.append("|".join(r.get(c, "") for c in cols))
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def build_example_income_statement_by_department(seed: int) -> list[dict[str, str]]:
    """
    Tiny worked example: revenue + expenses by department.
    Uses deterministic pseudo-random numbers (seeded).
    """
    rng = random.Random(seed)

    depts = ["SALES", "OPS"]
    # revenue and expense in dollars (integers) for wow simplicity
    rows = []
    for d in depts:
        rev = _d(rng.randint(9000, 14000))
        exp = _d(rng.randint(5000, 9000))
        net = rev - exp
        rows.append(
            {
                "dept": d,
                "revenue": _dec_str(rev),
                "expenses": _dec_str(exp),
                "net_income": _dec_str(net),
            }
        )

    # total
    total_rev = sum(_d(r["revenue"]) for r in rows)
    total_exp = sum(_d(r["expenses"]) for r in rows)
    total_net = total_rev - total_exp
    rows.append(
        {
            "dept": "TOTAL",
            "revenue": _dec_str(total_rev),
            "expenses": _dec_str(total_exp),
            "net_income": _dec_str(total_net),
        }
    )
    return rows


def build_tables_md(
    master_rows: Sequence[dict[str, str]],
    seg_dims: Sequence[dict[str, str]],
    seg_vals: Sequence[dict[str, str]],
    is_dept: Sequence[dict[str, str]],
) -> str:
    s = []
    s.append("# Chapter 03 — Chart of Accounts as Schema (Quick Tables)\n")
    s.append("## Account master (first 12)\n")
    s.append(
        md_table(
            master_rows,
            ["code", "name", "account_type", "normal_side", "statement", "rollup_code", "track_department", "track_project"],
            max_rows=12,
        )
    )
    s.append("\n## Segment dimensions\n")
    s.append(md_table(seg_dims, ["dimension_code", "dimension_name", "required", "description"]))

    s.append("\n## Segment values\n")
    s.append(md_table(seg_vals, ["dimension_code", "value_code", "value_name"]))

    s.append("\n## Income statement by department (example)\n")
    s.append(md_table(is_dept, ["dept", "revenue", "expenses", "net_income"], max_rows=10))
    return "\n".join(s).rstrip() + "\n"


def build_lineage_mermaid() -> str:
    return """flowchart LR
  S[coa_schema.json] --> M[account_master.csv]
  S --> D[segment_dimensions.csv]
  S --> V[segment_values.csv]
  M --> X[checks.md]
  D --> X
  V --> X
  M --> T[tables.md]
  D --> T
  V --> T
  I[income_statement_by_department.csv] --> T
  S --> K[diagnostics.md]
  M --> K
  S --> A[manifest.json]
  M --> A
  D --> A
  V --> A
  I --> A
"""


def artifact_manifest(outdir: Path, files: Sequence[Path]) -> dict[str, object]:
    items = []
    for p in files:
        rel = p.relative_to(outdir).as_posix()
        b = p.read_bytes()
        items.append({"path": rel, "bytes": len(b), "sha256": sha256_bytes(b)})
    return {"artifacts": sorted(items, key=lambda x: x["path"])}


def write_ch03_accounts_schema(out_root: Path, seed: int) -> Path:
    outdir = out_root / "ch03AccountsSchema"
    ensure_dir(outdir)

    accounts = default_accounts()
    seg_dims, seg_vals_obj = default_segments()
    seg_vals = [
        {"dimension_code": v.dimension_code, "value_code": v.value_code, "value_name": v.value_name}
        for v in seg_vals_obj
    ]

    # core outputs
    schema_path = outdir / "coa_schema.json"
    write_json(schema_path, schema_dict())

    master_rows = build_account_master_rows(accounts)
    master_path = outdir / "account_master.csv"
    write_csv(
        master_path,
        master_rows,
        [
            "code",
            "name",
            "account_type",
            "normal_side",
            "statement",
            "rollup_code",
            "is_contra",
            "is_active",
            "track_department",
            "track_project",
            "description",
        ],
    )

    seg_dims_path = outdir / "segment_dimensions.csv"
    write_csv(seg_dims_path, seg_dims, ["dimension_code", "dimension_name", "required", "description"])

    seg_vals_path = outdir / "segment_values.csv"
    write_csv(seg_vals_path, seg_vals, ["dimension_code", "value_code", "value_name"])

    is_dept_rows = build_example_income_statement_by_department(seed)
    is_dept_path = outdir / "income_statement_by_department.csv"
    write_csv(is_dept_path, is_dept_rows, ["dept", "revenue", "expenses", "net_income"])

    # checks
    checks = validate_accounts(accounts)
    checks_path = outdir / "checks.md"
    write_text(checks_path, "# Checks\n\n" + "\n".join(f"- {c}" for c in checks) + "\n")

    # tables
    tables_path = outdir / "tables.md"
    write_text(tables_path, build_tables_md(master_rows, seg_dims, seg_vals, is_dept_rows))

    # diagnostics
    master_hash = canonical_master_hash(master_rows)
    schema_hash = sha256_file(schema_path)
    diag_path = outdir / "diagnostics.md"
    write_text(
        diag_path,
        "\n".join(
            [
                "# Diagnostics",
                "",
                "## Canonical hashes",
                f"- account_master canonical sha256: `{master_hash}`",
                f"- coa_schema.json sha256: `{schema_hash}`",
                "",
                "## Notes",
                "- The COA is treated as a schema: constraints + metadata, not just a list of names.",
                "- `rollup_code` enables hierarchical reporting (e.g., BS/IS sections).",
                "- Segments (department/project) are schema metadata that future chapters can join on.",
                "",
            ]
        )
        + "\n",
    )

    # lineage
    lineage_path = outdir / "lineage.mmd"
    write_text(lineage_path, build_lineage_mermaid())

    # run meta
    run_meta_path = outdir / "run_meta.json"
    write_json(
        run_meta_path,
        {
            "chapter": "ch03AccountsSchema",
            "module": "ledgerloom.chapters.ch03_chart_of_accounts_schema",
            "seed": seed,
        },
    )

    # summary
    summary_path = outdir / "summary.md"
    write_text(
        summary_path,
        "\n".join(
            [
                "# Chapter 03 — Chart of Accounts as Schema",
                "",
                "## What you built",
                "- A COA schema (`coa_schema.json`) describing fields + constraints",
                "- An account master table (`account_master.csv`) for joins + validation",
                "- Segment dimensions + values (`segment_dimensions.csv`, `segment_values.csv`)",
                "- A tiny worked example (`income_statement_by_department.csv`)",
                "",
                "## Wow artifacts",
                "- `checks.md` (invariants you can trust)",
                "- `tables.md` (instant visual tour)",
                "- `diagnostics.md` (hash proofs + design notes)",
                "- `manifest.json` (inventory + sha256)",
                "- `lineage.mmd` (data lineage diagram)",
                "",
            ]
        )
        + "\n"
    )

    # manifest
    manifest_path = outdir / "manifest.json"
    files = [
        schema_path,
        master_path,
        seg_dims_path,
        seg_vals_path,
        is_dept_path,
        checks_path,
        tables_path,
        diag_path,
        lineage_path,
        run_meta_path,
        summary_path,
    ]
    write_json(manifest_path, artifact_manifest(outdir, files))

    return outdir


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LedgerLoom Chapter 03 (Alt): Chart of Accounts as Schema")
    p.add_argument("--outdir", type=str, required=True, help="Root output dir (chapter writes to <outdir>/ch03AccountsSchema)")
    p.add_argument("--seed", type=int, default=123, help="Seed for deterministic example numbers")
    args = p.parse_args(list(argv) if argv is not None else None)

    out_root = Path(args.outdir)
    outdir = write_ch03_accounts_schema(out_root, seed=args.seed)
    print(f"Wrote LedgerLoom Chapter 03 (COA schema) artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

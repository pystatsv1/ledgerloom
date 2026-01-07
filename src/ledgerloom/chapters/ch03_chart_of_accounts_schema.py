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
from pathlib import Path
from typing import Sequence

from ledgerloom.engine import COASchema
from ledgerloom.artifacts import manifest_items, sha256_file, write_csv_dicts, write_json, write_text
from ledgerloom.trust.pipeline import emit_trust_artifacts


def write_csv(path: Path, rows: Sequence[dict[str, str]], fieldnames: Sequence[str]) -> None:
    # Keep the chapter-local function name for readability in the narrative.
    write_csv_dicts(path, rows, fieldnames=fieldnames)


def md_table(rows: Sequence[dict[str, str]], cols: Sequence[str], max_rows: int = 10) -> str:
    head = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |\n"
    body = []
    for r in rows[:max_rows]:
        body.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return head + sep + "\n".join(body) + ("\n" if body else "")


def build_tables_md(
    master_rows: Sequence[dict[str, str]],
    seg_dims: Sequence[dict[str, str]],
    seg_vals: Sequence[dict[str, str]],
    is_dept_rows: Sequence[dict[str, str]],
) -> str:
    parts = [
        "# Tables (quick visual tour)",
        "",
        "## Account master (first rows)",
        md_table(
            master_rows,
            [
                "code",
                "name",
                "account_type",
                "normal_side",
                "statement",
                "rollup_code",
                "is_contra",
            ],
            max_rows=12,
        ),
        "",
        "## Segment dimensions",
        md_table(seg_dims, ["dimension_code", "dimension_name", "required", "description"], max_rows=10),
        "",
        "## Segment values",
        md_table(seg_vals, ["dimension_code", "value_code", "value_name"], max_rows=20),
        "",
        "## Worked example: Income statement by department",
        md_table(is_dept_rows, ["dept", "revenue", "expenses", "net_income"], max_rows=10),
        "",
    ]
    return "\n".join(parts)


def build_lineage_mermaid() -> str:
    return """flowchart LR
  A[default_accounts + default_segments] --> B[account_master.csv\n(dimension)]
  A --> C[segment_dimensions.csv\n(dimension)]
  A --> D[segment_values.csv\n(dimension)]
  B --> E[income_statement_by_department.csv\n(example view)]
  C --> E
  D --> E
  B --> F[checks.md\n(schema constraints)]
  A --> G[coa_schema.json\n(schema JSON)]
  G --> F
  B --> H[tables.md\n(preview)]
  C --> H
  D --> H
  E --> H
"""


def write_ch03_accounts_schema(out_root: Path, seed: int) -> Path:
    outdir = out_root / "ch03AccountsSchema"
    outdir.mkdir(parents=True, exist_ok=True)

    coa = COASchema.default()

    # core outputs
    schema_path = outdir / "coa_schema.json"
    write_json(schema_path, coa.schema_dict())

    master_rows = coa.account_master_rows()
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

    seg_dims = list(coa.segment_dimensions)
    seg_dims_path = outdir / "segment_dimensions.csv"
    write_csv(seg_dims_path, seg_dims, ["dimension_code", "dimension_name", "required", "description"])

    seg_vals = coa.segment_value_rows()
    seg_vals_path = outdir / "segment_values.csv"
    write_csv(seg_vals_path, seg_vals, ["dimension_code", "value_code", "value_name"])

    is_dept_rows = coa.example_income_statement_by_department(seed)
    is_dept_path = outdir / "income_statement_by_department.csv"
    write_csv(is_dept_path, is_dept_rows, ["dept", "revenue", "expenses", "net_income"])

    # checks
    checks = coa.validate_checks()
    checks_path = outdir / "checks.md"
    write_text(checks_path, "# Checks\n\n" + "\n".join(f"- {c}" for c in checks) + "\n")

    # tables
    tables_path = outdir / "tables.md"
    write_text(tables_path, build_tables_md(master_rows, seg_dims, seg_vals, is_dept_rows))

    # diagnostics
    master_hash = coa.canonical_master_hash()
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

    # run meta (written via trust pipeline)
    run_meta = {
        "chapter": "ch03AccountsSchema",
        "module": "ledgerloom.chapters.ch03_chart_of_accounts_schema",
        "seed": seed,
    }

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
        + "\n",
    )

    # manifest (written via trust pipeline; includes run_meta + summary)
    def _manifest_payload(d: Path) -> dict[str, object]:
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
            d / "run_meta.json",
            summary_path,
        ]
        return {
            "root": d.as_posix(),
            "items": manifest_items(d, files, name_key="path"),
        }

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

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

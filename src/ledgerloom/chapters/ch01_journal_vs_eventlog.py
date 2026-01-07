from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ledgerloom.artifacts import write_csv_df, write_text
from ledgerloom.core import Entry, Posting
from ledgerloom.io_jsonl import write_jsonl
from ledgerloom.reports import balance_sheet, income_statement, trial_balance
from ledgerloom.chart import account_root
from ledgerloom.engine import LedgerEngine
from ledgerloom.trust.pipeline import (
    emit_trust_artifacts,
    manifest_artifacts_from_specs,
    run_meta_artifacts_from_names,
)


def build_demo_entries() -> list[Entry]:
    # Tiny "small business" story:
    # 1) Invoice a client for services (AR up, revenue up)
    # 2) Client pays the invoice (cash up, AR down)
    # 3) Pay a software bill (expense up, cash down)
    return [
        Entry(
            dt=date(2026, 1, 2),
            narration="Invoice client for services",
            postings=[
                Posting("Assets:AccountsReceivable", debit=Decimal("1000.00")),
                Posting("Revenue:Services", credit=Decimal("1000.00")),
            ],
            meta={"doc": "INV-0001", "entry_id": "E001"},
        ),
        Entry(
            dt=date(2026, 1, 10),
            narration="Client payment received",
            postings=[
                Posting("Assets:Cash", debit=Decimal("1000.00")),
                Posting("Assets:AccountsReceivable", credit=Decimal("1000.00")),
            ],
            meta={"doc": "RCPT-0001", "entry_id": "E002"},
        ),
        Entry(
            dt=date(2026, 1, 15),
            narration="Pay SaaS subscription",
            postings=[
                Posting("Expenses:Software", debit=Decimal("50.00")),
                Posting("Assets:Cash", credit=Decimal("50.00")),
            ],
            meta={"doc": "BILL-0001", "entry_id": "E003"},
        ),
    ]


ARTIFACT_SPECS: list[dict[str, str]] = [
    {
        "name": "ledger.jsonl",
        "format": "jsonl",
        "kind": "event_log",
        "description": "Canonical append-only event log (one JSON object per entry).",
    },
    {
        "name": "eventlog.jsonl",
        "format": "jsonl",
        "kind": "event_log",
        "description": "Alias of ledger.jsonl (friendly name used in README/VISION).",
    },
    {
        "name": "journal.csv",
        "format": "csv",
        "kind": "view",
        "description": "Traditional journal view (one row per posting, debit/credit columns).",
    },
    {
        "name": "ledger_view.csv",
        "format": "csv",
        "kind": "view",
        "description": "Derived ledger view (running balances; think: database view).",
    },
    {
        "name": "trial_balance.csv",
        "format": "csv",
        "kind": "check",
        "description": "Trial balance (account totals; validates double-entry + aggregation).",
    },
    {
        "name": "income_statement.csv",
        "format": "csv",
        "kind": "report",
        "description": "Income statement derived from the trial balance.",
    },
    {
        "name": "balance_sheet.csv",
        "format": "csv",
        "kind": "report",
        "description": "Balance sheet derived from the trial balance (includes Check = A-(L+E)).",
    },
    {
        "name": "entry_explanations.md",
        "format": "md",
        "kind": "memo",
        "description": "Human-friendly explanation of each entry (inspectable + teachable).",
    },
    {
        "name": "assumptions.md",
        "format": "md",
        "kind": "memo",
        "description": "Small-scope assumptions + what is intentionally NOT modeled yet.",
    },
    {
        "name": "checks.md",
        "format": "md",
        "kind": "check",
        "description": "Invariant results (balanced entries, equation check, row counts).",
    },
    {
        "name": "entry_balancing.csv",
        "format": "csv",
        "kind": "check",
        "description": "Per-entry debit/credit totals (should net to 0 for every entry).",
    },
    {
        "name": "account_rollup.csv",
        "format": "csv",
        "kind": "view",
        "description": "Roll-up totals by account root (Assets/Liabilities/Equity/Revenue/Expenses).",
    },
    {
        "name": "root_bar_chart.md",
        "format": "md",
        "kind": "chart",
        "description": "Tiny text chart (bars) for root roll-ups—quick visual sanity check.",
    },
    {
        "name": "tables.md",
        "format": "md",
        "kind": "table",
        "description": "Key tables rendered as Markdown (journal, trial balance, statements).",
    },
    {
        "name": "lineage.mmd",
        "format": "mmd",
        "kind": "diagram",
        "description": "Mermaid diagram showing lineage: events → views → checks/reports.",
    },
    {
        "name": "run_meta.json",
        "format": "json",
        "kind": "manifest",
        "description": "Reproducible metadata: hashes, sizes, and counts.",
    },
    {
        "name": "manifest.json",
        "format": "json",
        "kind": "manifest",
        "description": "Human- and machine-friendly manifest describing all artifacts.",
    },
    {
        "name": "summary.md",
        "format": "md",
        "kind": "memo",
        "description": "Short chapter memo: what was generated + why it matters.",
    },
]


def explain_entry(e: Entry) -> str:
    # A human-friendly explanation showing both views.
    lines: list[str] = []
    lines.append(f"## {e.dt.isoformat()} — {e.narration}\n")
    lines.append("| Account | Debit | Credit |\n|---|---:|---:|\n")
    for p in e.postings:
        lines.append(f"| `{p.account}` | {p.debit} | {p.credit} |\n")
    lines.append("\nThis is a balanced entry (sum debits == sum credits).\n")
    return "".join(lines)


def _fmt(d: Decimal) -> str:
    return format(d, "f")


def _md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """Render a DataFrame as a Markdown table (deterministic)."""
    if max_rows is not None:
        df = df.head(max_rows)

    # Ensure stable column order and stable row order.
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |\n"
    rows = []
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(str(r[c]) for c in cols) + " |\n")
    return header + sep + "".join(rows)


def _bar(value: Decimal, scale: Decimal, width: int = 18) -> str:
    """Text bar (unicode blocks) for quick visuals; deterministic."""
    if scale <= 0:
        return ""
    n = int(min(width, (abs(value) / scale) * Decimal(width)))
    return "█" * n


def _root_rollup(tb: dict[str, Decimal]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for acct, amt in tb.items():
        root = account_root(acct)
        out[root] = out.get(root, Decimal("0")) + amt
    return dict(sorted(out.items()))


def _write_assumptions(outdir: Path) -> None:
    write_text(
        outdir / "assumptions.md",
        """# Assumptions + scope (Chapter 01)

This chapter is a **tiny, deterministic** accounting demo intended to be:

- small enough to read in one sitting
- rich enough to show real accounting structure
- strict enough to enforce invariants (like tests)

## What is modeled

- a micro "services" business
- three events: invoice → payment → expense
- a minimal chart of accounts (Assets/Revenue/Expenses)
- reports: trial balance, income statement, balance sheet

## What is *not* modeled yet (intentionally)

- sales tax / VAT
- payroll
- accrual adjustments / closing entries
- bank reconciliation

Those arrive in later chapters. The goal here is to nail the mental model:

> **store immutable events → derive views + checks → trust outputs**
""",
    )


def _write_lineage(outdir: Path) -> None:
    write_text(
        outdir / "lineage.mmd",
        """%% LedgerLoom Chapter 01 lineage
flowchart LR
  A[ledger.jsonl\n(event log)] --> B[journal.csv\n(view)]
  A --> C[ledger_view.csv\n(view)]
  A --> D[trial_balance.csv\n(check/view)]
  D --> E[income_statement.csv\n(report)]
  D --> F[balance_sheet.csv\n(report)]
  A --> G[entry_balancing.csv\n(invariant check)]
  D --> H[account_rollup.csv\n(view)]
  A --> I[entry_explanations.md\n(memo)]
  A --> J[tables.md\n(markdown tables)]
  A --> K[checks.md\n(invariant results)]
  A --> L[run_meta.json + manifest.json\n(reproducibility)]
""",
    )


def _write_tables(
    outdir: Path,
    journal_df: pd.DataFrame,
    tb_df: pd.DataFrame,
    is_df: pd.DataFrame,
    bs_df: pd.DataFrame,
) -> None:
    parts: list[str] = []
    parts.append("# Tables (Chapter 01)\n\n")
    parts.append(
        "These are the same artifacts you can open as CSV—rendered here as Markdown for quick scanning.\n\n"
    )

    parts.append("## Journal (first 12 rows)\n\n")
    parts.append(_md_table(journal_df, max_rows=12))
    parts.append("\n\n")

    parts.append("## Trial balance\n\n")
    parts.append(_md_table(tb_df))
    parts.append("\n\n")

    parts.append("## Income statement\n\n")
    parts.append(_md_table(is_df))
    parts.append("\n\n")

    parts.append("## Balance sheet\n\n")
    parts.append(_md_table(bs_df))
    parts.append("\n\n")

    write_text(outdir / "tables.md", "".join(parts))


def _write_checks(
    outdir: Path,
    entries: list[Entry],
    entry_balance_df: pd.DataFrame,
    bs: dict[str, Decimal],
) -> None:
    # Small invariant summary, designed to be readable in PRs.
    all_balanced = all(abs(Decimal(x)) == Decimal("0") for x in entry_balance_df["delta"].tolist())
    check = bs.get("Check", Decimal("0"))

    lines: list[str] = []
    lines.append("# Checks (Chapter 01)\n\n")
    lines.append("These checks are intentionally redundant with tests—so you can eyeball them.\n\n")
    lines.append("## Double-entry invariant\n\n")
    lines.append(
        f"- Per-entry debits == credits: **{'PASS' if all_balanced else 'FAIL'}** (see `entry_balancing.csv`)\n"
    )
    lines.append(f"- Entries: {len(entries)}\n")
    lines.append(f"- Postings: {sum(len(e.postings) for e in entries)}\n\n")
    lines.append("## Accounting equation (after close)\n\n")
    lines.append(
        f"- Balance sheet Check (A - (L + EquityAfterClose)) == 0: **{'PASS' if check == 0 else 'FAIL'}**\n"
    )
    lines.append(f"- Check value: `{check}`\n\n")
    lines.append("## Reproducibility\n\n")
    lines.append("- Artifact hashes and sizes are in `run_meta.json` and `manifest.json`.\n")
    write_text(outdir / "checks.md", "".join(lines))


def _write_root_rollup(outdir: Path, tb: dict[str, Decimal]) -> None:
    rr = _root_rollup(tb)
    df = pd.DataFrame(
        [{"root": k, "amount": _fmt(v)} for k, v in rr.items()],
        columns=["root", "amount"],
    )
    write_csv_df(outdir / "account_rollup.csv", df)

    # A tiny text chart: bars scaled to the max absolute value.
    max_abs = max((abs(v) for v in rr.values()), default=Decimal("0"))
    scale = max_abs if max_abs > 0 else Decimal("1")

    lines = ["# Root roll-up chart (Chapter 01)\n\n"]
    lines.append("This is a fast, visual sanity-check of totals by account type.\n\n")
    lines.append("| root | amount | bar |\n|---|---:|---|\n")
    for root, amt in rr.items():
        bar = _bar(amt, scale)
        lines.append(f"| `{root}` | {amt} | {bar} |\n")
    write_text(outdir / "root_bar_chart.md", "".join(lines))


def entries_to_journal_df(entries: list[Entry]) -> pd.DataFrame:
    """Traditional 'journal' view: one row per posting with explicit debit/credit columns."""
    rows: list[dict[str, str]] = []
    for i, e in enumerate(entries, start=1):
        entry_id = str(e.meta.get("entry_id") or f"E{i:03d}")
        for j, p in enumerate(e.postings, start=1):
            rows.append(
                {
                    "entry_id": entry_id,
                    "line_no": str(j),
                    "dt": e.dt.isoformat(),
                    "narration": e.narration,
                    "account": p.account,
                    "debit": _fmt(p.debit),
                    "credit": _fmt(p.credit),
                    "doc": e.meta.get("doc", ""),
                }
            )
    return pd.DataFrame(rows)


def entries_to_ledger_view_df(entries: list[Entry]) -> pd.DataFrame:
    """Developer 'ledger view': derived, type-aware running balances by account.

    This is intentionally a *derived view* computed from the Engine's postings fact
    table, to keep Chapter 01 aligned with the reusable core.
    """

    engine = LedgerEngine()
    postings = engine.postings_fact_table(entries)

    # Map entry_id -> doc metadata for nice traceability.
    doc_by_entry = {str(e.meta.get("entry_id", "")): str(e.meta.get("doc", "")) for e in entries}

    rows: list[dict[str, str]] = []
    running: dict[str, Decimal] = {}

    # postings are already sorted (date, entry_id, line_no) deterministically.
    for _, r in postings.iterrows():
        acct = str(r["account"])
        delta = Decimal(str(r["signed_delta"]))
        running[acct] = running.get(acct, Decimal("0")) + delta

        eid = str(r["entry_id"])
        rows.append(
            {
                "dt": str(r["date"]),
                "entry_id": eid,
                "line_no": str(r["line_no"]),
                "narration": str(r["narration"]),
                "account_root": str(r["root"]),
                "account": acct,
                "debit": str(r["debit"]),
                "credit": str(r["credit"]),
                "delta": _fmt(delta),
                "balance": _fmt(running[acct]),
                "doc": doc_by_entry.get(eid, ""),
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=Path("outputs/ledgerloom"))
    ap.add_argument("--seed", type=int, default=123)  # reserved for future
    args = ap.parse_args()

    outdir: Path = args.outdir / "ch01"
    outdir.mkdir(parents=True, exist_ok=True)

    entries = build_demo_entries()

    # --- Event log (append-only facts) ---
    ledger_path = outdir / "ledger.jsonl"  # kept for backwards compatibility
    eventlog_path = outdir / "eventlog.jsonl"  # name used in VISION.md
    write_jsonl(ledger_path, entries)
    # Duplicate the same content under the VISION/README-friendly name.
    eventlog_path.write_bytes(ledger_path.read_bytes())

    # --- Journal + derived ledger view ---
    journal_df = entries_to_journal_df(entries)
    write_csv_df(outdir / "journal.csv", journal_df)

    ledger_view_df = entries_to_ledger_view_df(entries)
    write_csv_df(outdir / "ledger_view.csv", ledger_view_df)

    tb = trial_balance(entries)
    is_ = income_statement(tb)
    bs = balance_sheet(tb)

    write_csv_df(outdir / "trial_balance.csv", pd.Series(tb).rename_axis("account").reset_index(name="amount"))
    write_csv_df(outdir / "income_statement.csv", pd.Series(is_).rename_axis("account").reset_index(name="amount"))
    write_csv_df(outdir / "balance_sheet.csv", pd.Series(bs).rename_axis("account").reset_index(name="amount"))

    # --- Extra "wow" artifacts (tables, checks, chart) ---
    entry_balance_rows: list[dict[str, str]] = []
    for i, e in enumerate(entries, start=1):
        entry_id = str(e.meta.get("entry_id") or f"E{i:03d}")
        debits = sum((p.debit for p in e.postings), Decimal("0"))
        credits = sum((p.credit for p in e.postings), Decimal("0"))
        entry_balance_rows.append(
            {
                "entry_id": entry_id,
                "dt": e.dt.isoformat(),
                "doc": e.meta.get("doc", ""),
                "narration": e.narration,
                "debits": _fmt(debits),
                "credits": _fmt(credits),
                "delta": _fmt(debits - credits),
            }
        )
    entry_balance_df = pd.DataFrame(entry_balance_rows)
    write_csv_df(outdir / "entry_balancing.csv", entry_balance_df)

    _write_assumptions(outdir)
    _write_root_rollup(outdir, tb)
    _write_lineage(outdir)

    # Render Markdown tables from the CSV-ish views.
    tb_df = pd.Series(tb).rename_axis("account").reset_index(name="amount")
    is_df = pd.Series(is_).rename_axis("account").reset_index(name="amount")
    bs_df = pd.Series(bs).rename_axis("account").reset_index(name="amount")
    _write_tables(outdir, journal_df, tb_df, is_df, bs_df)

    _write_checks(outdir, entries, entry_balance_df, bs)

    expl = "\n".join(explain_entry(e) for e in entries)
    write_text(outdir / "entry_explanations.md", expl)

    # Write summary before hashing artifacts in run_meta/manifest.
    summary_lines = [
        "# LedgerLoom Chapter 01 — Journal vs Event Log\n",
        "\n",
        "This demo is intentionally small, deterministic, and **inspectable**.\n",
        "It shows how the same accounting facts can be represented as:\n",
        "\n",
        "- a traditional **journal** (tabular debits/credits)\n",
        "- an append-only **event log** (JSONL)\n",
        "- a derived **ledger view** (a projection / database view)\n",
        "\n",
        "## What was generated\n",
        *[f"- `{spec['name']}` — {spec['description']}\n" for spec in ARTIFACT_SPECS],
        "\n",
        "## Key invariant\n",
        "- Each entry is balanced: debits == credits.\n",
        "- The balance sheet includes a `Check` value that should be 0 (A = L + E after close).\n",
        "\n",
        "## Next\n",
        "Chapter 02 shows that debits/credits are an **encoding choice** — including a signed representation.\n",
    ]
    write_text(outdir / "summary.md", "".join(summary_lines))

    # --- Meta + summary ("wow" + reproducibility) ---
    artifact_names = [spec["name"] for spec in ARTIFACT_SPECS]

    # run_meta.json should not attempt to hash itself or manifest.json.
    run_meta_names = [
        n for n in artifact_names if n not in {"run_meta.json", "manifest.json"}
    ]
    run_meta: dict[str, Any] = {
        "chapter": "01",
        "seed": int(args.seed),
        "n_entries": len(entries),
        "n_postings": int(sum(len(e.postings) for e in entries)),
        "artifacts": run_meta_artifacts_from_names(outdir, run_meta_names),
    }

    # manifest.json can include run_meta.json, but should not attempt to hash itself.
    manifest_specs = [
        spec for spec in ARTIFACT_SPECS if spec["name"] != "manifest.json"
    ]

    def _manifest_payload(p: Path) -> dict[str, Any]:
        return {
            "chapter": "01",
            "seed": int(args.seed),
            "n_entries": len(entries),
            "n_postings": int(sum(len(e.postings) for e in entries)),
            "artifacts": manifest_artifacts_from_specs(p, manifest_specs),
            "manifest_file": {
                "name": "manifest.json",
                "note": "The manifest does not include a hash (or size) of itself to avoid recursion.",
            },
            "notes": {
                "determinism": (
                    "All artifacts are derived solely from entries and are stable across platforms."
                ),
                "event_log": (
                    "The canonical event log is ledger.jsonl; eventlog.jsonl is an alias."
                ),
            },
        }

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    print(f"Wrote LedgerLoom Chapter 01 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
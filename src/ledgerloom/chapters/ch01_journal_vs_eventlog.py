from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ledgerloom.chart import account_root, signed_delta
from ledgerloom.core import Entry, Posting
from ledgerloom.io_jsonl import write_jsonl
from ledgerloom.reports import balance_sheet, income_statement, trial_balance


def build_demo_entries() -> list[Entry]:
    # Tiny "small business" story:
    # 1) Invoice a client for services (AR up, income up)
    # 2) Client pays the invoice (cash up, AR down)
    # 3) Pay a software bill (expense up, cash down)
    return [
        Entry(
            dt=date(2026, 1, 2),
            narration="Invoice client for services",
            postings=[
                Posting("Assets:AccountsReceivable", debit=Decimal("1000.00")),
                Posting("Income:Services", credit=Decimal("1000.00")),
            ],
            meta={"doc": "INV-0001"},
        ),
        Entry(
            dt=date(2026, 1, 10),
            narration="Client payment received",
            postings=[
                Posting("Assets:Cash", debit=Decimal("1000.00")),
                Posting("Assets:AccountsReceivable", credit=Decimal("1000.00")),
            ],
            meta={"doc": "RCPT-0001"},
        ),
        Entry(
            dt=date(2026, 1, 15),
            narration="Pay SaaS subscription",
            postings=[
                Posting("Expenses:Software", debit=Decimal("50.00")),
                Posting("Assets:Cash", credit=Decimal("50.00")),
            ],
            meta={"doc": "BILL-0001"},
        ),
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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def entries_to_journal_df(entries: list[Entry]) -> pd.DataFrame:
    """Traditional 'journal' view: one row per posting with explicit debit/credit columns."""
    rows: list[dict[str, str]] = []
    for i, e in enumerate(entries, start=1):
        entry_id = f"E{i:03d}"
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
    """Developer 'ledger view': derived, type-aware running balances by account."""
    rows: list[dict[str, str]] = []
    running: dict[str, Decimal] = {}

    for i, e in enumerate(entries, start=1):
        entry_id = f"E{i:03d}"
        for j, p in enumerate(e.postings, start=1):
            delta = signed_delta(p.account, p.debit, p.credit)
            running[p.account] = running.get(p.account, Decimal("0")) + delta
            rows.append(
                {
                    "dt": e.dt.isoformat(),
                    "entry_id": entry_id,
                    "line_no": str(j),
                    "narration": e.narration,
                    "account_root": account_root(p.account),
                    "account": p.account,
                    "debit": _fmt(p.debit),
                    "credit": _fmt(p.credit),
                    "delta": _fmt(delta),
                    "balance": _fmt(running[p.account]),
                    "doc": e.meta.get("doc", ""),
                }
            )

    # Deterministic ordering: already built in entry order; keep stable.
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
    eventlog_path.write_text(ledger_path.read_text(encoding="utf-8"), encoding="utf-8")

    # --- Journal + derived ledger view ---
    journal_df = entries_to_journal_df(entries)
    journal_df.to_csv(outdir / "journal.csv", index=False)

    ledger_view_df = entries_to_ledger_view_df(entries)
    ledger_view_df.to_csv(outdir / "ledger_view.csv", index=False)

    tb = trial_balance(entries)
    is_ = income_statement(tb)
    bs = balance_sheet(tb)

    pd.Series(tb).rename_axis("account").reset_index(name="amount").to_csv(
        outdir / "trial_balance.csv", index=False
    )
    pd.Series(is_).rename_axis("account").reset_index(name="amount").to_csv(
        outdir / "income_statement.csv", index=False
    )
    pd.Series(bs).rename_axis("account").reset_index(name="amount").to_csv(
        outdir / "balance_sheet.csv", index=False
    )

    expl = "\n".join(explain_entry(e) for e in entries)
    (outdir / "entry_explanations.md").write_text(expl, encoding="utf-8")

    # --- Meta + summary ("wow" + reproducibility) ---
    artifacts = [
        "ledger.jsonl",
        "eventlog.jsonl",
        "journal.csv",
        "ledger_view.csv",
        "trial_balance.csv",
        "income_statement.csv",
        "balance_sheet.csv",
        "entry_explanations.md",
    ]
    meta = {
        "chapter": "01",
        "seed": int(args.seed),
        "n_entries": len(entries),
        "n_postings": int(sum(len(e.postings) for e in entries)),
        "artifacts": [
            {
                "name": name,
                "sha256": _sha256(outdir / name),
                "bytes": int((outdir / name).stat().st_size),
            }
            for name in artifacts
        ],
    }
    (outdir / "run_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

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
        *[f"- `{name}`\n" for name in artifacts],
        "\n",
        "## Key invariant\n",
        "- Each entry is balanced: debits == credits.\n",
        "- The balance sheet includes a `Check` value that should be 0 (A = L + E after close).\n",
        "\n",
        "## Next\n",
        "Chapter 02 shows that debits/credits are an **encoding choice** — including a signed representation.\n",
    ]
    (outdir / "summary.md").write_text("".join(summary_lines), encoding="utf-8")

    print(f"Wrote LedgerLoom Chapter 01 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

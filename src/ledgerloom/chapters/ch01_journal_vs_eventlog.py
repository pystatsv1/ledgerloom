from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=Path("outputs/ledgerloom"))
    ap.add_argument("--seed", type=int, default=123)  # reserved for future
    args = ap.parse_args()

    outdir: Path = args.outdir / "ch01"
    outdir.mkdir(parents=True, exist_ok=True)

    entries = build_demo_entries()
    ledger_path = outdir / "ledger.jsonl"
    write_jsonl(ledger_path, entries)

    tb = trial_balance(entries)
    is_ = income_statement(tb)
    bs = balance_sheet(tb)

    pd.Series(tb, name="balance").to_csv(outdir / "trial_balance.csv")
    pd.Series(is_, name="amount").to_csv(outdir / "income_statement.csv")
    pd.Series(bs, name="amount").to_csv(outdir / "balance_sheet.csv")

    expl = "\n".join(explain_entry(e) for e in entries)
    (outdir / "entry_explanations.md").write_text(expl, encoding="utf-8")

    print(f"Wrote LedgerLoom Chapter 01 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

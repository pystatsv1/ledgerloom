"""LedgerLoom Chapter 02 — Debits/Credits encoding (wide vs long).

This chapter demonstrates how the same accounting facts can be represented in
different tabular encodings and still compile into the same canonical journal
(entries + postings).

Outputs (written under outputs/ledgerloom/ch02 by default):
- encoding_wide.csv
- encoding_long.csv
- journal_from_wide.jsonl
- journal_from_long.jsonl
- trial_balance.csv
- income_statement.csv
- balance_sheet.csv
- run_meta.json
- summary.md
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.io_jsonl import write_jsonl
from ledgerloom.reports import balance_sheet, income_statement, trial_balance


def _d(x: object) -> Decimal:
    """Convert a number-like value to a 2-decimal Decimal."""
    return Decimal(str(x)).quantize(Decimal("0.01"))


def build_demo_wide(seed: int = 123) -> pd.DataFrame:
    """Build a tiny, meaningful transaction set in a *wide* debit/credit encoding."""

    # Note: Seed is included for API symmetry / future expansion; this demo is deterministic.
    _ = seed

    rows = [
        {
            "tx_id": "T001",
            "dt": "2025-01-01",
            "narration": "Owner invests cash",
            "debit_account": "Assets:Cash",
            "debit_amount": "5000.00",
            "credit_account": "Equity:OwnerCapital",
            "credit_amount": "5000.00",
        },
        {
            "tx_id": "T002",
            "dt": "2025-01-02",
            "narration": "Buy inventory on account",
            "debit_account": "Assets:Inventory",
            "debit_amount": "1200.00",
            "credit_account": "Liabilities:AccountsPayable",
            "credit_amount": "1200.00",
        },
        {
            "tx_id": "T003",
            "dt": "2025-01-05",
            "narration": "Pay supplier (partial)",
            "debit_account": "Liabilities:AccountsPayable",
            "debit_amount": "300.00",
            "credit_account": "Assets:Cash",
            "credit_amount": "300.00",
        },
        {
            "tx_id": "T004",
            "dt": "2025-01-10",
            "narration": "Invoice customer for sale",
            "debit_account": "Assets:AccountsReceivable",
            "debit_amount": "800.00",
            "credit_account": "Income:Sales",
            "credit_amount": "800.00",
        },
        {
            "tx_id": "T005",
            "dt": "2025-01-10",
            "narration": "Record cost of goods sold",
            "debit_account": "Expenses:COGS",
            "debit_amount": "500.00",
            "credit_account": "Assets:Inventory",
            "credit_amount": "500.00",
        },
        {
            "tx_id": "T006",
            "dt": "2025-01-15",
            "narration": "Receive customer payment",
            "debit_account": "Assets:Cash",
            "debit_amount": "800.00",
            "credit_account": "Assets:AccountsReceivable",
            "credit_amount": "800.00",
        },
    ]

    return pd.DataFrame(rows)


def wide_to_entries(df: pd.DataFrame) -> list[Entry]:
    """Compile wide encoding rows into canonical LedgerLoom entries."""

    required = {
        "tx_id",
        "dt",
        "narration",
        "debit_account",
        "debit_amount",
        "credit_account",
        "credit_amount",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Wide encoding missing columns: {sorted(missing)}")

    entries: list[Entry] = []
    # Preserve row order for determinism.
    for row in df.to_dict(orient="records"):
        debit_amt = _d(row["debit_amount"])
        credit_amt = _d(row["credit_amount"])

        entry = Entry(
            dt=date.fromisoformat(str(row["dt"])),
            narration=str(row["narration"]),
            postings=[
                Posting(account=str(row["debit_account"]), debit=debit_amt),
                Posting(account=str(row["credit_account"]), credit=credit_amt),
            ],
            meta={"tx_id": str(row["tx_id"])},
        )
        entry.validate_balanced()
        entries.append(entry)

    return entries


def wide_to_long(df_wide: pd.DataFrame) -> pd.DataFrame:
    """Convert wide debit/credit rows into a long (side, amount) encoding."""

    debit = df_wide[
        ["tx_id", "dt", "narration", "debit_account", "debit_amount"]
    ].rename(
        columns={
            "debit_account": "account",
            "debit_amount": "amount",
        }
    )
    debit["side"] = "debit"

    credit = df_wide[
        ["tx_id", "dt", "narration", "credit_account", "credit_amount"]
    ].rename(
        columns={
            "credit_account": "account",
            "credit_amount": "amount",
        }
    )
    credit["side"] = "credit"

    df_long = pd.concat([debit, credit], ignore_index=True)

    side_order = df_long["side"].map({"debit": 0, "credit": 1}).astype(int)
    df_long = df_long.assign(_side_order=side_order).sort_values(
        ["dt", "tx_id", "_side_order", "account"],
        kind="mergesort",
    )
    return df_long.drop(columns=["_side_order"]).reset_index(drop=True)


def long_to_entries(df: pd.DataFrame) -> list[Entry]:
    """Compile long encoding rows into canonical LedgerLoom entries."""

    required = {"tx_id", "dt", "narration", "account", "side", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Long encoding missing columns: {sorted(missing)}")

    # Deterministic ordering: tx rows in dt/tx_id order, with debits before credits.
    side_order = df["side"].map({"debit": 0, "credit": 1})
    if side_order.isna().any():
        bad = sorted(set(df.loc[side_order.isna(), "side"].astype(str)))
        raise ValueError(f"Invalid side values in long encoding: {bad}")
    df2 = df.assign(_side_order=side_order.astype(int)).sort_values(
        ["dt", "tx_id", "_side_order", "account"],
        kind="mergesort",
    )

    entries: list[Entry] = []
    for tx_id, g in df2.groupby("tx_id", sort=False):
        first = g.iloc[0]
        postings: list[Posting] = []
        for _, r in g.iterrows():
            amt = _d(r["amount"])
            if r["side"] == "debit":
                postings.append(Posting(account=str(r["account"]), debit=amt))
            else:
                postings.append(Posting(account=str(r["account"]), credit=amt))

        entry = Entry(
            dt=date.fromisoformat(str(first["dt"])),
            narration=str(first["narration"]),
            postings=postings,
            meta={"tx_id": str(tx_id)},
        )
        entry.validate_balanced()
        entries.append(entry)

    return entries


def _write_reports(out_ch_dir: Path, entries: Iterable[Entry]) -> None:
    tb = trial_balance(entries)
    is_ = income_statement(tb)
    bs = balance_sheet(tb)

    pd.Series(tb).rename_axis("account").reset_index(name="amount").to_csv(
        out_ch_dir / "trial_balance.csv", index=False
    )

    pd.Series(is_).rename_axis("account").reset_index(name="amount").to_csv(
        out_ch_dir / "income_statement.csv", index=False
    )

    pd.Series(bs).rename_axis("account").reset_index(name="amount").to_csv(
        out_ch_dir / "balance_sheet.csv", index=False
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ledgerloom-ch02",
        description="LedgerLoom Chapter 02 demo: wide vs long debits/credits encoding.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("outputs/ledgerloom"),
        help="Output directory root (default: outputs/ledgerloom)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Deterministic seed (reserved for future expansion). Default: 123.",
    )
    args = parser.parse_args(argv)

    out_ch_dir = args.outdir / "ch02"
    out_ch_dir.mkdir(parents=True, exist_ok=True)

    df_wide = build_demo_wide(seed=args.seed)
    df_long = wide_to_long(df_wide)

    entries_from_wide = wide_to_entries(df_wide)
    entries_from_long = long_to_entries(df_long)

    # Write encodings
    df_wide.to_csv(out_ch_dir / "encoding_wide.csv", index=False)
    df_long.to_csv(out_ch_dir / "encoding_long.csv", index=False)

    # Write compiled journals
    write_jsonl(out_ch_dir / "journal_from_wide.jsonl", entries_from_wide)
    write_jsonl(out_ch_dir / "journal_from_long.jsonl", entries_from_long)

    # Reports (use the canonical entries, but both should match)
    _write_reports(out_ch_dir, entries_from_wide)

    # Meta + summary (kept simple, but useful for demos / reproducibility)
    meta = {
        "chapter": "02",
        "seed": int(args.seed),
        "n_entries": len(entries_from_wide),
        "n_postings": int(sum(len(e.postings) for e in entries_from_wide)),
        "wide_columns": list(df_wide.columns),
        "long_columns": list(df_long.columns),
        "entries_match": entries_from_wide == entries_from_long,
    }
    (out_ch_dir / "run_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary_lines = [
        "# LedgerLoom Chapter 02 — Debits/Credits encoding\n",
        "This demo shows that different table encodings can compile into the same canonical journal.\n",
        "## What was generated\n",
        f"- Wide rows: {len(df_wide)}\n",
        f"- Long rows: {len(df_long)}\n",
        f"- Entries: {len(entries_from_wide)}\n",
        "\n",
        "## Key result\n",
        f"- journal_from_wide.jsonl == journal_from_long.jsonl: **{meta['entries_match']}**\n",
        "\n",
        "## Next\n",
        "Chapter 03 will introduce a Chart of Accounts schema to validate account names and types.\n",
    ]
    (out_ch_dir / "summary.md").write_text("".join(summary_lines), encoding="utf-8")

    print(f"Wrote LedgerLoom Chapter 02 artifacts -> {out_ch_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

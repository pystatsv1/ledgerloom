"""LedgerLoom Chapter 02 — Debits/Credits as encoding (wide, long, signed).

Goal
----
Show that the same accounting facts can be encoded in multiple tabular shapes and
still compile into the *same canonical journal* (entries + postings).

Why this matters
----------------
Real-world accounting data arrives in different layouts depending on the source:

- "Wide" exports (one row per transaction) with explicit debit/credit columns
- "Long" exports (many rows per transaction) with a side flag (D/C)
- Analytics-friendly tables with a single signed amount column

LedgerLoom treats these as *encodings* that can all be compiled into a canonical,
validated journal. The accounting comes from invariants, not from column names.

Outputs (written under outputs/ledgerloom/ch02 by default)
---------------------------------------------------------
Encodings:
- encoding_wide.csv
- encoding_long.csv
- encoding_signed.csv

Canonical journals (byte-identical JSONL across encodings):
- journal_from_wide.jsonl
- journal_from_long.jsonl
- journal_from_signed.jsonl

Reports (derived from canonical entries):
- trial_balance.csv
- income_statement.csv
- balance_sheet.csv

WOW artifacts (developer-friendly proofs + tour):
- diagnostics.md
- checks.md
- tables.md
- lineage.mmd
- manifest.json
- run_meta.json
- summary.md
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import pandas as pd

from ledgerloom.artifacts import sha256_file, write_csv_df, write_text
from ledgerloom.core import Entry, Posting
from ledgerloom.io_jsonl import write_jsonl
from ledgerloom.reports import balance_sheet, income_statement, trial_balance
from ledgerloom.trust.pipeline import emit_trust_artifacts, manifest_artifacts_from_specs


def _d(x: object) -> Decimal:
    """Convert a number-like value to a 2-decimal Decimal."""
    return Decimal(str(x)).quantize(Decimal("0.01"))


def _md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    """Render a DataFrame as a Markdown table (deterministic)."""
    if max_rows is not None:
        df = df.head(max_rows)

    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |\n"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |\n"
    rows: list[str] = []
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(str(r[c]) for c in cols) + " |\n")
    return header + sep + "".join(rows)


def _sorted_postings(postings: list[Posting]) -> list[Posting]:
    """Deterministic ordering so different encodings serialize identically."""

    def key(p: Posting) -> tuple[int, str, Decimal]:
        side = 0 if p.debit != _d(0) else 1
        amt = p.debit if side == 0 else p.credit
        return (side, p.account, amt)

    return sorted(postings, key=key)


ARTIFACT_SPECS: list[dict[str, str]] = [
    {
        "name": "encoding_wide.csv",
        "format": "csv",
        "kind": "encoding",
        "description": "Wide D/C encoding (one row per tx).",
    },
    {
        "name": "encoding_long.csv",
        "format": "csv",
        "kind": "encoding",
        "description": "Long encoding (many rows per tx; side + amount).",
    },
    {
        "name": "encoding_signed.csv",
        "format": "csv",
        "kind": "encoding",
        "description": "Signed encoding (single signed_amount column).",
    },
    {
        "name": "journal_from_wide.jsonl",
        "format": "jsonl",
        "kind": "journal",
        "description": "Canonical journal compiled from wide encoding.",
    },
    {
        "name": "journal_from_long.jsonl",
        "format": "jsonl",
        "kind": "journal",
        "description": "Canonical journal compiled from long encoding.",
    },
    {
        "name": "journal_from_signed.jsonl",
        "format": "jsonl",
        "kind": "journal",
        "description": "Canonical journal compiled from signed encoding.",
    },
    {
        "name": "trial_balance.csv",
        "format": "csv",
        "kind": "report",
        "description": "Trial balance from canonical entries.",
    },
    {
        "name": "income_statement.csv",
        "format": "csv",
        "kind": "report",
        "description": "Income statement (Revenue/Expenses/NetIncome).",
    },
    {
        "name": "balance_sheet.csv",
        "format": "csv",
        "kind": "report",
        "description": "Balance sheet (Assets/Liabilities/Equity + NetIncome).",
    },
    {
        "name": "diagnostics.md",
        "format": "md",
        "kind": "proof",
        "description": "Hashes + narrative explanation of invariants and equivalence.",
    },
    {
        "name": "checks.md",
        "format": "md",
        "kind": "proof",
        "description": "PASS/FAIL invariant checks (human-readable).",
    },
    {
        "name": "tables.md",
        "format": "md",
        "kind": "tour",
        "description": "Markdown tables for encodings + reports (quick visual tour).",
    },
    {
        "name": "lineage.mmd",
        "format": "mmd",
        "kind": "diagram",
        "description": "Mermaid lineage diagram: encodings → journal → reports.",
    },
    {
        "name": "run_meta.json",
        "format": "json",
        "kind": "meta",
        "description": "Reproducibility metadata (seed, counts, equivalence booleans).",
    },
    {
        "name": "manifest.json",
        "format": "json",
        "kind": "meta",
        "description": "Artifact manifest with hashes + sizes.",
    },
    {
        "name": "summary.md",
        "format": "md",
        "kind": "meta",
        "description": "Short chapter summary + pointers to outputs.",
    },
]


def _manifest_payload(out_ch_dir: Path) -> dict[str, object]:
    """Build the manifest payload (hashes + sizes) for the chapter.

    The trust pipeline writer injects the schema field.
    """

    # Do not attempt to hash manifest.json itself.
    # We also skip artifacts that do not yet exist (e.g., summary.md is written after
    # the manifest in this chapter).
    specs = [
        s
        for s in ARTIFACT_SPECS
        if s["name"] != "manifest.json" and (out_ch_dir / s["name"]).exists()
    ]
    return {
        "chapter": "ch02",
        "artifacts": manifest_artifacts_from_specs(out_ch_dir, specs),
    }


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
            "narration": "Buy inventory on credit",
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
            "narration": "Sell inventory (invoice customer)",
            "debit_account": "Assets:AccountsReceivable",
            "debit_amount": "800.00",
            "credit_account": "Revenue:Sales",
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
    for _, row in df.iterrows():
        entry = Entry(
            dt=date.fromisoformat(str(row["dt"])),
            narration=str(row["narration"]),
            postings=_sorted_postings(
                [
                    Posting(
                        account=str(row["debit_account"]),
                        debit=_d(row["debit_amount"]),
                        credit=_d(0),
                    ),
                    Posting(
                        account=str(row["credit_account"]),
                        debit=_d(0),
                        credit=_d(row["credit_amount"]),
                    ),
                ]
            ),
            meta={"entry_id": str(row["tx_id"]), "tx_id": str(row["tx_id"])},
        )
        entries.append(entry)

    return entries


def wide_to_long(df_wide: pd.DataFrame) -> pd.DataFrame:
    """Convert wide encoding into long encoding (one posting per row)."""
    rows: list[dict[str, str]] = []
    for _, r in df_wide.iterrows():
        tx_id = str(r["tx_id"])
        rows.append(
            {
                "tx_id": tx_id,
                "dt": str(r["dt"]),
                "narration": str(r["narration"]),
                "side": "debit",
                "account": str(r["debit_account"]),
                "amount": format(_d(r["debit_amount"]), "f"),
            }
        )
        rows.append(
            {
                "tx_id": tx_id,
                "dt": str(r["dt"]),
                "narration": str(r["narration"]),
                "side": "credit",
                "account": str(r["credit_account"]),
                "amount": format(_d(r["credit_amount"]), "f"),
            }
        )

    df_long = pd.DataFrame(rows)

    # Deterministic ordering (so CSV is stable).
    side_order = df_long["side"].map({"debit": 0, "credit": 1})
    df_long = (
        df_long.assign(_side_order=side_order)
        .sort_values(["tx_id", "_side_order", "account"])
        .drop(columns=["_side_order"])
    )
    return df_long.reset_index(drop=True)


def long_to_signed(df_long: pd.DataFrame) -> pd.DataFrame:
    """Convert long encoding into signed encoding (single signed_amount column)."""
    rows: list[dict[str, str]] = []
    for _, r in df_long.iterrows():
        side = str(r["side"])
        amt = _d(r["amount"])
        signed_amt = amt if side == "debit" else -amt
        rows.append(
            {
                "tx_id": str(r["tx_id"]),
                "dt": str(r["dt"]),
                "narration": str(r["narration"]),
                "account": str(r["account"]),
                "signed_amount": format(signed_amt, "f"),
            }
        )

    df_signed = pd.DataFrame(rows)

    # Deterministic ordering: debits (positive) first, then credits (negative).
    side_order = df_signed["signed_amount"].map(lambda s: 0 if Decimal(str(s)) >= 0 else 1)
    df_signed = (
        df_signed.assign(_side_order=side_order)
        .sort_values(["tx_id", "_side_order", "account"])
        .drop(columns=["_side_order"])
    )
    return df_signed.reset_index(drop=True)


def signed_to_entries(df: pd.DataFrame) -> list[Entry]:
    """Compile signed encoding rows into canonical entries.

    Signed encoding is *journal-centric*:
    - debits are positive signed_amount
    - credits are negative signed_amount

    We reconstruct debit/credit columns for LedgerLoom's canonical postings.
    """
    required = {"tx_id", "dt", "narration", "account", "signed_amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Signed encoding missing columns: {sorted(missing)}")

    entries: list[Entry] = []

    for tx_id, g in df.groupby("tx_id", sort=True):
        g = g.sort_values(["account", "signed_amount"]).reset_index(drop=True)
        postings: list[Posting] = []
        for _, r in g.iterrows():
            sa = Decimal(str(r["signed_amount"]))
            if sa >= 0:
                postings.append(Posting(account=str(r["account"]), debit=_d(sa), credit=_d(0)))
            else:
                postings.append(Posting(account=str(r["account"]), debit=_d(0), credit=_d(-sa)))



        postings = _sorted_postings(postings)

        entry = Entry(
            dt=date.fromisoformat(str(g.loc[0, "dt"])),
            narration=str(g.loc[0, "narration"]),
            postings=postings,
            meta={"entry_id": str(tx_id), "tx_id": str(tx_id)},
        )
        entries.append(entry)

    return entries


def long_to_entries(df: pd.DataFrame) -> list[Entry]:
    """Compile long encoding rows into canonical entries."""
    required = {"tx_id", "dt", "narration", "side", "account", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Long encoding missing columns: {sorted(missing)}")

    entries: list[Entry] = []
    for tx_id, g in df.groupby("tx_id", sort=True):
        postings: list[Posting] = []
        for _, r in g.iterrows():
            side = str(r["side"])
            amt = _d(r["amount"])
            if side == "debit":
                postings.append(Posting(account=str(r["account"]), debit=amt, credit=_d(0)))
            elif side == "credit":
                postings.append(Posting(account=str(r["account"]), debit=_d(0), credit=amt))
            else:
                raise ValueError(f"Unknown side: {side!r}")



        postings = _sorted_postings(postings)

        entry = Entry(
            dt=date.fromisoformat(str(g.iloc[0]["dt"])),
            narration=str(g.iloc[0]["narration"]),
            postings=postings,
            meta={"entry_id": str(tx_id), "tx_id": str(tx_id)},
        )
        entries.append(entry)

    return entries


def _compute_reports(entries: Iterable[Entry]) -> dict[str, dict[str, Decimal]]:
    tb = trial_balance(entries)
    is_ = income_statement(tb)
    bs = balance_sheet(tb)
    return {"trial_balance": tb, "income_statement": is_, "balance_sheet": bs}


def _write_reports(out_ch_dir: Path, reports: dict[str, dict[str, Decimal]]) -> None:
    tb = reports["trial_balance"]
    is_ = reports["income_statement"]
    bs = reports["balance_sheet"]

    write_csv_df(out_ch_dir / "trial_balance.csv", pd.Series(tb).rename_axis("account").reset_index(name="amount"))
    write_csv_df(out_ch_dir / "income_statement.csv", pd.Series(is_).rename_axis("account").reset_index(name="amount"))
    write_csv_df(out_ch_dir / "balance_sheet.csv", pd.Series(bs).rename_axis("account").reset_index(name="amount"))



def _write_lineage(out_ch_dir: Path) -> None:
    mermaid = """flowchart LR
  W[encoding_wide.csv\n(wide D/C)] --> L[encoding_long.csv\n(long: side+amount)]
  L --> S[encoding_signed.csv\n(signed_amount)]
  W --> JW[journal_from_wide.jsonl]
  L --> JL[journal_from_long.jsonl]
  S --> JS[journal_from_signed.jsonl]
  JW --> R[trial_balance.csv\n+ statements]
  JL --> R
  JS --> R
  JW --> D[diagnostics.md\n+ checks.md]
  JL --> D
  JS --> D
  R --> T[tables.md]
  D --> T
  T --> M[manifest.json\n(run_meta.json)]
"""
    write_text(out_ch_dir / "lineage.mmd", mermaid)


def _write_tables(
    out_ch_dir: Path,
    df_wide: pd.DataFrame,
    df_long: pd.DataFrame,
    df_signed: pd.DataFrame,
    reports: dict[str, dict[str, Decimal]],
) -> None:
    tb = pd.Series(reports["trial_balance"]).rename_axis("account").reset_index(name="amount")
    is_ = pd.Series(reports["income_statement"]).rename_axis("account").reset_index(name="amount")
    bs = pd.Series(reports["balance_sheet"]).rename_axis("account").reset_index(name="amount")

    lines: list[str] = []
    lines.append("# LedgerLoom Chapter 02 — Tables\n\n")
    lines.append("These tables are generated from the demo data so you can *see* the encodings and reports.\n\n")

    lines.append("## Wide encoding (one row per transaction)\n\n")
    lines.append(_md_table(df_wide, max_rows=None) + "\n")

    lines.append("## Long encoding (one row per posting)\n\n")
    lines.append(_md_table(df_long, max_rows=12) + "\n")

    lines.append("## Signed encoding (single numeric measure)\n\n")
    lines.append(_md_table(df_signed, max_rows=12) + "\n")

    lines.append("## Trial balance\n\n")
    lines.append(_md_table(tb.sort_values('account').reset_index(drop=True), max_rows=None) + "\n")

    lines.append("## Income statement\n\n")
    lines.append(_md_table(is_.reset_index(drop=True), max_rows=None) + "\n")

    lines.append("## Balance sheet\n\n")
    lines.append(_md_table(bs.reset_index(drop=True), max_rows=None) + "\n")

    write_text(out_ch_dir / "tables.md", "".join(lines))


def _write_checks(
    out_ch_dir: Path,
    df_wide: pd.DataFrame,
    df_long: pd.DataFrame,
    df_signed: pd.DataFrame,
    wide_hash: str,
    long_hash: str,
    signed_hash: str,
    reports_match: bool,
) -> None:
    # Invariants at the encoding level
    wide_bal = all(_d(r["debit_amount"]) == _d(r["credit_amount"]) for _, r in df_wide.iterrows())

    long_grp = df_long.groupby("tx_id", sort=True)
    long_bal = True
    for _, g in long_grp:
        deb = sum(_d(x) for x in g.loc[g["side"] == "debit", "amount"])
        cred = sum(_d(x) for x in g.loc[g["side"] == "credit", "amount"])
        long_bal = long_bal and (deb == cred)

    signed_grp = df_signed.groupby("tx_id", sort=True)
    signed_bal = True
    for _, g in signed_grp:
        s = sum(Decimal(str(x)) for x in g["signed_amount"])
        signed_bal = signed_bal and (s == 0)

    journals_equal = (wide_hash == long_hash == signed_hash)

    def fmt(ok: bool) -> str:
        return "PASS ✅" if ok else "FAIL ❌"

    lines = [
        "# LedgerLoom Chapter 02 — Checks\n\n",
        "This file is a compact PASS/FAIL view of the chapter invariants.\n\n",
        "## Encoding invariants\n",
        f"- Wide rows balance per transaction (debit_amount == credit_amount): **{fmt(wide_bal)}**\n",
        f"- Long rows balance per transaction (sum debits == sum credits): **{fmt(long_bal)}**\n",
        f"- Signed rows balance per transaction (sum signed_amount == 0): **{fmt(signed_bal)}**\n\n",
        "## Journal equivalence\n",
        (
            f"- journal_from_wide.jsonl == journal_from_long.jsonl "
            f"== journal_from_signed.jsonl: **{fmt(journals_equal)}**\n\n"
        ),
        "## Report equivalence\n",
        f"- Trial balance / statements are identical across encodings: **{fmt(reports_match)}**\n\n",
        "If a check fails, inspect `diagnostics.md` and `tables.md`.\n",
    ]
    write_text(out_ch_dir / "checks.md", "".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ledgerloom-ch02",
        description="LedgerLoom Chapter 02 demo: wide vs long vs signed debits/credits encoding.",
    )
    parser.add_argument("--outdir", type=Path, default=Path("outputs/ledgerloom"), help="Base output directory.")
    parser.add_argument("--seed", type=int, default=123, help="Seed for deterministic demo data.")
    args = parser.parse_args(argv)

    out_ch_dir = args.outdir / "ch02"
    out_ch_dir.mkdir(parents=True, exist_ok=True)

    df_wide = build_demo_wide(seed=args.seed)
    df_long = wide_to_long(df_wide)
    df_signed = long_to_signed(df_long)

    entries_from_wide = wide_to_entries(df_wide)
    entries_from_long = long_to_entries(df_long)
    entries_from_signed = signed_to_entries(df_signed)

    # Write encodings
    write_csv_df(out_ch_dir / "encoding_wide.csv", df_wide)
    write_csv_df(out_ch_dir / "encoding_long.csv", df_long)
    write_csv_df(out_ch_dir / "encoding_signed.csv", df_signed)

    # Write compiled journals (deterministic JSONL)
    write_jsonl(out_ch_dir / "journal_from_wide.jsonl", entries_from_wide)
    write_jsonl(out_ch_dir / "journal_from_long.jsonl", entries_from_long)
    write_jsonl(out_ch_dir / "journal_from_signed.jsonl", entries_from_signed)

    # Hashes (for equivalence proofs)
    wide_hash = sha256_file(out_ch_dir / "journal_from_wide.jsonl")
    long_hash = sha256_file(out_ch_dir / "journal_from_long.jsonl")
    signed_hash = sha256_file(out_ch_dir / "journal_from_signed.jsonl")

    # Reports (use the canonical entries, but all journals should match)
    reports_w = _compute_reports(entries_from_wide)
    reports_l = _compute_reports(entries_from_long)
    reports_s = _compute_reports(entries_from_signed)
    reports_match = (reports_w == reports_l == reports_s)

    # Write reports once (they are identical if reports_match is True).
    _write_reports(out_ch_dir, reports_w)

    # Diagnostics (human-friendly) — invariants + equivalence checks.
    diag_lines: list[str] = []
    diag_lines.extend(
        [
            "# LedgerLoom Chapter 02 — Diagnostics\n\n",
            "This file captures the *invariants* and *equivalence checks* for the chapter artifacts.\n\n",
            "## What we are proving\n",
            "1) Wide, long, and signed tables can all represent the *same* accounting facts.\n",
            "2) Those facts compile into the same canonical journal (entries + postings).\n",
            "3) The reports derived from the journal are therefore identical.\n\n",
            "## SHA-256 hashes (canonical journals)\n",
            f"- journal_from_wide.jsonl: `{wide_hash}`\n",
            f"- journal_from_long.jsonl: `{long_hash}`\n",
            f"- journal_from_signed.jsonl: `{signed_hash}`\n\n",
            f"- wide == long: **{wide_hash == long_hash}**\n",
            f"- wide == signed: **{wide_hash == signed_hash}**\n\n",
            "## Invariants (high level)\n",
            "- Each transaction balances (debits equal credits).\n",
            "- Signed encoding balances by construction (sum(signed_amount) == 0 per tx).\n",
            "- Canonical entries validate as balanced double-entry bookkeeping.\n",
            "- Trial balance and statements are stable and identical across encodings.\n\n",
            "## Why signed encoding is useful\n",
            "A signed amount column is convenient in analytics pipelines because postings become a\n",
            "single numeric measure that can be aggregated, filtered, and modeled. The constraints\n",
            "(sum to 0 per transaction; balances roll up correctly) are what make it accounting.\n\n",
            "## Next\n",
            "Open `tables.md` for a quick visual tour, `checks.md` for PASS/FAIL, and `lineage.mmd`\n",
            "for the artifact flow.\n",
        ]
    )
    write_text(out_ch_dir / "diagnostics.md", "".join(diag_lines))

    # WOW artifacts
    _write_checks(out_ch_dir, df_wide, df_long, df_signed, wide_hash, long_hash, signed_hash, reports_match)
    _write_tables(out_ch_dir, df_wide, df_long, df_signed, reports_w)
    _write_lineage(out_ch_dir)

    # Meta + summary (useful for demos / reproducibility)
    meta = {
        "chapter": "ch02",
        "seed": args.seed,
        "n_transactions": int(df_wide.shape[0]),
        "n_long_rows": int(df_long.shape[0]),
        "n_signed_rows": int(df_signed.shape[0]),
        "n_entries": len(entries_from_wide),
        "entries_match_all": (wide_hash == long_hash == signed_hash),
        "reports_match_all": reports_match,
        "hash_wide": wide_hash,
        "hash_long": long_hash,
        "hash_signed": signed_hash,
    }
    # Trust artifacts (run_meta.json + manifest.json).
    # Note: We emit these *before* summary.md so the manifest only describes files
    # that already exist at this point (preserving historic behavior).
    emit_trust_artifacts(out_ch_dir, run_meta=meta, manifest=_manifest_payload)

    summary_lines = [
        "# LedgerLoom Chapter 02 — Debits/Credits as encoding\n\n",
        "This demo shows that multiple table shapes can compile into the same canonical journal.\n\n",
        "## What was generated\n",
        "- Encodings: `encoding_wide.csv`, `encoding_long.csv`, `encoding_signed.csv`\n",
        "- Journals: `journal_from_wide.jsonl`, `journal_from_long.jsonl`, `journal_from_signed.jsonl`\n",
        "- Reports: `trial_balance.csv`, `income_statement.csv`, `balance_sheet.csv`\n",
        "- Proofs + tour: `checks.md`, `diagnostics.md`, `tables.md`, `lineage.mmd`\n",
        "- Meta: `run_meta.json`, `manifest.json`\n\n",
        "## Proof in one line\n",
        (
            f"- journal_from_wide.jsonl == journal_from_long.jsonl "
            f"== journal_from_signed.jsonl: **{meta['entries_match_all']}**\n\n"
        ),
        "## Next\n",
        "Chapter 03 will introduce a Chart of Accounts schema to validate account names and types.\n",
    ]
    write_text(out_ch_dir / "summary.md", "".join(summary_lines))

    print(f"Wrote LedgerLoom Chapter 02 artifacts -> {out_ch_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

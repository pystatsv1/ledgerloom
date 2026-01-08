"""
LedgerLoom — Chapter 03: Posting to the Ledger

Goal:
- Take a journal (wide debit/credit)
- Post it to a general ledger (per-account running balances)
- Produce a trial balance from ending balances
- Emit "wow" artifacts: checks, tables, lineage, manifest, diagnostics

Run:
  python -m ledgerloom.chapters.ch03_posting_to_ledger --outdir outputs/ledgerloom --seed 123

Optional:
  python -m ledgerloom.chapters.ch03_posting_to_ledger --outdir outputs/ledgerloom --in_journal path/to/journal.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable, Sequence

from ledgerloom.artifacts import manifest_items, sha256_bytes
from ledgerloom.trust.pipeline import emit_trust_artifacts

getcontext().prec = 28


D0 = Decimal("0")


def _d(x: str | int | Decimal) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _dec_str(x: Decimal) -> str:
    # stable string representation (no exponent surprises)
    q = x.quantize(Decimal("0.01")) if x.as_tuple().exponent < 0 else x
    s = format(q, "f")
    # normalize "-0.00" => "0.00"
    if s.startswith("-0") and Decimal(s) == D0:
        return "0.00"
    if "." not in s:
        return f"{s}.00"
    # ensure 2 decimals for currency-like outputs
    whole, frac = s.split(".", 1)
    frac = (frac + "00")[:2]
    return f"{whole}.{frac}"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, s: str) -> None:
    path.write_text(s, encoding="utf-8", newline="\n")


def write_json(path: Path, obj: object) -> None:
    write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: Sequence[dict[str, str]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        # Force LF line endings for byte-stable artifacts across platforms.
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
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
class JournalLine:
    entry_id: str
    entry_date: str  # ISO yyyy-mm-dd
    memo: str
    line_no: int
    account: str
    debit: Decimal
    credit: Decimal

    @property
    def signed_amount(self) -> Decimal:
        # debit positive, credit negative
        return self.debit - self.credit


NORMAL_BALANCE: dict[str, str] = {
    # Assets
    "Cash": "debit",
    "Accounts Receivable": "debit",
    "Inventory": "debit",
    "Equipment": "debit",
    # Liabilities
    "Accounts Payable": "credit",
    "Notes Payable": "credit",
    # Equity
    "Owner Capital": "credit",
    "Retained Earnings": "credit",
    # Revenue
    "Sales Revenue": "credit",
    # Expenses
    "COGS": "debit",
    "Rent Expense": "debit",
    "Wages Expense": "debit",
}


def account_type(acct: str) -> str:
    if acct in {"Cash", "Accounts Receivable", "Inventory", "Equipment"}:
        return "asset"
    if acct in {"Accounts Payable", "Notes Payable"}:
        return "liability"
    if acct in {"Owner Capital", "Retained Earnings"}:
        return "equity"
    if acct in {"Sales Revenue"}:
        return "revenue"
    return "expense"


def normal_side(acct: str) -> str:
    return NORMAL_BALANCE.get(acct, "debit")


def normal_signed(acct: str, signed: Decimal) -> Decimal:
    # convert to "normal positive" balance convention
    return signed if normal_side(acct) == "debit" else -signed


def generate_demo_journal(seed: int) -> list[JournalLine]:
    """
    Deterministic small-business mini-cycle journal.
    The specific numbers are less important than the invariants.
    """
    rng = random.Random(seed)
    start = date(2025, 1, 1)

    def amt(lo: int, hi: int) -> Decimal:
        return _d(rng.randint(lo, hi))

    entries: list[list[tuple[str, Decimal, Decimal]]] = []

    # 1) Owner invests cash
    a1 = amt(8000, 12000)
    entries.append(
        [
            ("Cash", a1, D0),
            ("Owner Capital", D0, a1),
        ]
    )

    # 2) Buy inventory on account
    a2 = amt(1200, 2500)
    entries.append(
        [
            ("Inventory", a2, D0),
            ("Accounts Payable", D0, a2),
        ]
    )

    # 3) Buy equipment (part cash, part note)
    a3 = amt(1500, 3000)
    a3_cash = (a3 * _d("0.40")).quantize(Decimal("1"))
    a3_note = a3 - a3_cash
    entries.append(
        [
            ("Equipment", a3, D0),
            ("Cash", D0, a3_cash),
            ("Notes Payable", D0, a3_note),
        ]
    )

    # 4) Make a sale for cash (with COGS)
    sale = amt(900, 1600)
    cogs = (sale * _d("0.55")).quantize(Decimal("1"))
    entries.append(
        [
            ("Cash", sale, D0),
            ("Sales Revenue", D0, sale),
        ]
    )
    entries.append(
        [
            ("COGS", cogs, D0),
            ("Inventory", D0, cogs),
        ]
    )

    # 5) Pay rent
    rent = amt(600, 900)
    entries.append(
        [
            ("Rent Expense", rent, D0),
            ("Cash", D0, rent),
        ]
    )

    # 6) Pay part of AP
    pay_ap = (a2 * _d("0.50")).quantize(Decimal("1"))
    entries.append(
        [
            ("Accounts Payable", pay_ap, D0),
            ("Cash", D0, pay_ap),
        ]
    )

    # 7) Pay wages
    wages = amt(300, 650)
    entries.append(
        [
            ("Wages Expense", wages, D0),
            ("Cash", D0, wages),
        ]
    )

    lines: list[JournalLine] = []
    for i, entry_lines in enumerate(entries, start=1):
        entry_id = f"E{i:03d}"
        entry_date = (start + timedelta(days=i * 3)).isoformat()
        memo = {
            1: "Owner investment",
            2: "Inventory purchase on account",
            3: "Equipment purchase (cash + note)",
            4: "Cash sale",
            5: "Record COGS for sale",
            6: "Pay portion of accounts payable",
            7: "Pay wages",
        }.get(i, "Journal entry")

        for j, (acct, dr, cr) in enumerate(entry_lines, start=1):
            lines.append(
                JournalLine(
                    entry_id=entry_id,
                    entry_date=entry_date,
                    memo=memo,
                    line_no=j,
                    account=acct,
                    debit=dr,
                    credit=cr,
                )
            )
    return lines


def read_journal_csv(path: Path) -> list[JournalLine]:
    """
    Accepts a journal.csv shaped like:
      entry_id,entry_date,memo,line_no,account,debit,credit

    If line_no is missing, we assign within entry.
    """
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    # normalize column names
    cols = {c.strip(): c for c in rows[0].keys()} if rows else {}
    def col(name: str) -> str:
        for k in cols:
            if k.lower() == name.lower():
                return cols[k]
        raise KeyError(f"Missing column: {name}")

    have_line_no = any("line_no" in (k or "").lower() for k in cols)

    lines: list[JournalLine] = []
    per_entry_counter: dict[str, int] = {}
    for r in rows:
        entry_id = (r.get(col("entry_id")) or "").strip()
        entry_date = (r.get(col("entry_date")) or "").strip()
        memo = (r.get(col("memo")) or "").strip()
        account = (r.get(col("account")) or "").strip()
        debit = _d((r.get(col("debit")) or "0").strip() or "0")
        credit = _d((r.get(col("credit")) or "0").strip() or "0")

        if have_line_no:
            ln_raw = (r.get(col("line_no")) or "").strip()
            line_no = int(ln_raw) if ln_raw else 1
        else:
            per_entry_counter[entry_id] = per_entry_counter.get(entry_id, 0) + 1
            line_no = per_entry_counter[entry_id]

        lines.append(
            JournalLine(
                entry_id=entry_id,
                entry_date=entry_date,
                memo=memo,
                line_no=line_no,
                account=account,
                debit=debit,
                credit=credit,
            )
        )
    return lines


def canonical_journal_hash(lines: Sequence[JournalLine]) -> str:
    # stable ordering: entry_id, line_no, account
    s = []
    for ln in sorted(lines, key=lambda x: (x.entry_id, x.line_no, x.account)):
        s.append(
            "|".join(
                [
                    ln.entry_id,
                    ln.entry_date,
                    ln.memo,
                    str(ln.line_no),
                    ln.account,
                    _dec_str(ln.debit),
                    _dec_str(ln.credit),
                ]
            )
        )
    return sha256_bytes(("\n".join(s) + "\n").encode("utf-8"))


def post_to_ledger(lines: Sequence[JournalLine]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Returns:
      ledger_long rows
      account_balances rows (ending per account)
    """
    # sort by date then entry then line
    ordered = sorted(lines, key=lambda x: (x.entry_date, x.entry_id, x.line_no, x.account))

    # running balances per account in "normal positive" convention
    running: dict[str, Decimal] = {}
    ledger_rows: list[dict[str, str]] = []

    for ln in ordered:
        signed = ln.signed_amount
        ns = normal_signed(ln.account, signed)
        running[ln.account] = running.get(ln.account, D0) + ns

        ledger_rows.append(
            {
                "entry_date": ln.entry_date,
                "entry_id": ln.entry_id,
                "line_no": str(ln.line_no),
                "account": ln.account,
                "account_type": account_type(ln.account),
                "normal_side": normal_side(ln.account),
                "memo": ln.memo,
                "debit": _dec_str(ln.debit),
                "credit": _dec_str(ln.credit),
                "signed_amount": _dec_str(signed),
                "normal_signed_amount": _dec_str(ns),
                "running_balance": _dec_str(running[ln.account]),
            }
        )

    bal_rows: list[dict[str, str]] = []
    for acct in sorted(running.keys()):
        bal_rows.append(
            {
                "account": acct,
                "account_type": account_type(acct),
                "normal_side": normal_side(acct),
                "ending_balance_normal": _dec_str(running[acct]),
            }
        )

    return ledger_rows, bal_rows


def ledger_wide_from_long(ledger_long: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for r in ledger_long:
        rows.append(
            {
                "entry_date": r["entry_date"],
                "entry_id": r["entry_id"],
                "line_no": r["line_no"],
                "account": r["account"],
                "memo": r["memo"],
                "debit": r["debit"],
                "credit": r["credit"],
                "running_balance": r["running_balance"],
            }
        )
    return rows


def trial_balance_from_balances(bal_rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    tb = []
    for r in bal_rows:
        bal = _d(r["ending_balance_normal"])
        side = r["normal_side"]  # normal balance side for the account
        # present TB using debit/credit columns
        if side == "debit":
            debit = bal if bal >= D0 else D0
            credit = -bal if bal < D0 else D0
        else:
            credit = bal if bal >= D0 else D0
            debit = -bal if bal < D0 else D0

        tb.append(
            {
                "account": r["account"],
                "account_type": r["account_type"],
                "normal_side": side,
                "debit": _dec_str(debit),
                "credit": _dec_str(credit),
            }
        )
    # stable ordering
    return sorted(tb, key=lambda x: (x["account_type"], x["account"]))


def sum_dc(lines: Iterable[JournalLine]) -> tuple[Decimal, Decimal]:
    dr = D0
    cr = D0
    for ln in lines:
        dr += ln.debit
        cr += ln.credit
    return dr, cr


def build_checks(lines: Sequence[JournalLine], tb_rows: Sequence[dict[str, str]]) -> list[str]:
    checks: list[str] = []

    # Check 1: each entry balances
    per_entry: dict[str, list[JournalLine]] = {}
    for ln in lines:
        per_entry.setdefault(ln.entry_id, []).append(ln)

    bad_entries = []
    for eid, ls in per_entry.items():
        dr, cr = sum_dc(ls)
        if dr != cr:
            bad_entries.append((eid, dr, cr))

    if bad_entries:
        checks.append("FAIL: entry_balances — some entries do not balance")
        for eid, dr, cr in bad_entries[:10]:
            checks.append(f"  - {eid}: debits={_dec_str(dr)} credits={_dec_str(cr)}")
    else:
        checks.append(f"PASS: entry_balances — {len(per_entry)} / {len(per_entry)} entries balance")

    # Check 2: trial balance totals match
    tb_dr = sum(_d(r["debit"]) for r in tb_rows)
    tb_cr = sum(_d(r["credit"]) for r in tb_rows)
    if tb_dr != tb_cr:
        checks.append("FAIL: trial_balance_totals — debits != credits")
        checks.append(f"  - TB debits={_dec_str(tb_dr)} credits={_dec_str(tb_cr)}")
    else:
        checks.append("PASS: trial_balance_totals — total debits equal total credits")
        checks.append(f"  - total={_dec_str(tb_dr)}")

    return checks


def build_lineage_mermaid() -> str:
    return """flowchart LR
  A[journal.csv] --> B[ledger_long.csv]
  B --> C[ledger_wide.csv]
  B --> D[account_balances.csv]
  D --> E[trial_balance.csv]
  A --> X[checks.md]
  E --> X
  A --> T[tables.md]
  B --> T
  E --> T
  A --> M[manifest.json]
  B --> M
  E --> M
"""


def build_tables_md(
    journal_rows: Sequence[dict[str, str]],
    ledger_long: Sequence[dict[str, str]],
    tb_rows: Sequence[dict[str, str]],
) -> str:
    s = []
    s.append("# Chapter 03 — Quick Tables\n")
    s.append("## Journal (first 10 lines)\n")
    s.append(md_table(journal_rows, ["entry_id", "entry_date", "memo", "line_no", "account", "debit", "credit"]))
    s.append("\n## Ledger (first 10 lines)\n")
    s.append(
        md_table(
            ledger_long,
            [
                "entry_date",
                "entry_id",
                "account",
                "debit",
                "credit",
                "normal_side",
                "running_balance",
            ],
        )
    )
    s.append("\n## Trial Balance\n")
    s.append(md_table(tb_rows, ["account_type", "account", "debit", "credit"]))
    return "\n".join(s).rstrip() + "\n"



def write_ch03_artifacts(out_root: Path, seed: int, in_journal: Path | None) -> Path:
    outdir = out_root / "ch03"
    ensure_dir(outdir)

    # choose input
    if in_journal is not None:
        lines = read_journal_csv(in_journal)
        source = f"journal_csv:{in_journal.as_posix()}"
    else:
        lines = generate_demo_journal(seed)
        source = "demo_journal"

    # emit journal.csv (canonical for this chapter)
    journal_rows = [
        {
            "entry_id": ln.entry_id,
            "entry_date": ln.entry_date,
            "memo": ln.memo,
            "line_no": str(ln.line_no),
            "account": ln.account,
            "debit": _dec_str(ln.debit),
            "credit": _dec_str(ln.credit),
        }
        for ln in sorted(lines, key=lambda x: (x.entry_id, x.line_no, x.account))
    ]
    journal_csv = outdir / "journal.csv"
    write_csv(journal_csv, journal_rows, ["entry_id", "entry_date", "memo", "line_no", "account", "debit", "credit"])

    # ledger + balances
    ledger_long, balances = post_to_ledger(lines)
    ledger_long_csv = outdir / "ledger_long.csv"
    write_csv(
        ledger_long_csv,
        ledger_long,
        [
            "entry_date",
            "entry_id",
            "line_no",
            "account",
            "account_type",
            "normal_side",
            "memo",
            "debit",
            "credit",
            "signed_amount",
            "normal_signed_amount",
            "running_balance",
        ],
    )

    ledger_wide = ledger_wide_from_long(ledger_long)
    ledger_wide_csv = outdir / "ledger_wide.csv"
    write_csv(
        ledger_wide_csv,
        ledger_wide,
        ["entry_date", "entry_id", "line_no", "account", "memo", "debit", "credit", "running_balance"],
    )

    balances_csv = outdir / "account_balances.csv"
    write_csv(balances_csv, balances, ["account", "account_type", "normal_side", "ending_balance_normal"])

    tb_rows = trial_balance_from_balances(balances)
    tb_csv = outdir / "trial_balance.csv"
    write_csv(tb_csv, tb_rows, ["account_type", "account", "normal_side", "debit", "credit"])

    # checks
    checks_lines = build_checks(lines, tb_rows)
    checks_md = outdir / "checks.md"
    write_text(checks_md, "# Chapter 03 — Checks\n\n" + "\n".join(f"- {c}" for c in checks_lines) + "\n")

    # tables
    tables_md = outdir / "tables.md"
    write_text(tables_md, build_tables_md(journal_rows, ledger_long, tb_rows))

    # lineage
    lineage = outdir / "lineage.mmd"
    write_text(lineage, build_lineage_mermaid())

    # diagnostics
    jhash = canonical_journal_hash(lines)
    diag = outdir / "diagnostics.md"
    write_text(
        diag,
        "\n".join(
            [
                "# Chapter 03 — Diagnostics",
                "",
                "## Canonical journal hash",
                f"- sha256: `{jhash}`",
                "",
                "## Notes",
                "- `signed_amount = debit - credit`",
                "- `normal_signed_amount` flips the sign for credit-normal accounts so *normal* balances are positive.",
                "- Trial balance is built from ending balances and must satisfy total debits == total credits.",
                "",
            ]
        )
        + "\n"
    )

    # run meta (written via trust pipeline)
    run_meta = {
        "chapter": "ch03",
        "module": "ledgerloom.chapters.ch03_posting_to_ledger",
        "seed": seed,
        "source": source,
    }

    # summary
    summary = outdir / "summary.md"
    write_text(
        summary,
        "\n".join(
            [
                "# Chapter 03 — Posting to the Ledger",
                "",
                "## What you built",
                "- A canonical journal (`journal.csv`)",
                "- A posted general ledger with running balances (`ledger_long.csv`, `ledger_wide.csv`)",
                "- Ending balances per account (`account_balances.csv`)",
                "- A trial balance (`trial_balance.csv`)",
                "",
                "## Wow artifacts",
                "- `checks.md` — PASS/FAIL accounting invariants",
                "- `tables.md` — quick “see it instantly” tables",
                "- `diagnostics.md` — hash proof + sign conventions",
                "- `lineage.mmd` — data lineage diagram (Mermaid)",
                "- `manifest.json` — artifact inventory + sha256",
                "",
            ]
        )
        + "\n"
    )

    # manifest (written via trust pipeline; includes run_meta + summary)
    def _manifest_payload(d: Path) -> dict[str, object]:
        files = [
            journal_csv,
            ledger_long_csv,
            ledger_wide_csv,
            balances_csv,
            tb_csv,
            checks_md,
            tables_md,
            diag,
            lineage,
            d / "run_meta.json",
            summary,
        ]
        # De-dupe in case of accidental repeats
        seen: set[str] = set()
        uniq: list[Path] = []
        for p in files:
            key = p.name
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        items = manifest_items(d, uniq, name_key="path")
        return {"artifacts": sorted(items, key=lambda x: str(x["path"]))}

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    return outdir


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="LedgerLoom Chapter 03: posting to the ledger")
    p.add_argument("--outdir", type=str, required=True, help="Root output dir (chapter writes to <outdir>/ch03)")
    p.add_argument("--seed", type=int, default=123, help="Random seed for deterministic demo data")
    p.add_argument("--in_journal", type=str, default=None, help="Optional path to journal.csv to post")
    args = p.parse_args(list(argv) if argv is not None else None)

    out_root = Path(args.outdir)
    in_journal = Path(args.in_journal) if args.in_journal else None

    outdir = write_ch03_artifacts(out_root, seed=args.seed, in_journal=in_journal)
    print(f"Wrote LedgerLoom Chapter 03 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
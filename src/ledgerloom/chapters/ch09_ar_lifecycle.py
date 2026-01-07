"""LedgerLoom Chapter 09: Accounts Receivable lifecycle (control + subledger).

This chapter starts from Chapter 08 post-close balances, creates an opening entry
for the next period (same concept as Chapter 08.5), then runs a tiny A/R cycle:

- Issue invoices (A/R control increases)
- Receive cash and apply to invoices (A/R control decreases)
- Build an A/R open-items subledger
- Reconcile subledger total to the A/R control account in the G/L

Outputs are deterministic for a fixed seed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine, LedgerEngineConfig
from ledgerloom.engine.money import cents_to_str, str_to_cents
from ledgerloom.artifacts import artifacts_map, write_csv_df, write_csv_dicts, write_json
from ledgerloom.trust.pipeline import emit_trust_artifacts

# Scenario layer (public): provides the shared "bookset" pipeline without
# cross-chapter imports.
from ledgerloom.scenarios import bookset_v1 as bookset


CHAPTER = "ch09"
PERIOD_START = date(2026, 2, 1)
PERIOD_END = date(2026, 2, 28)

AR_ACCT = "Assets:AccountsReceivable"
CASH_ACCT = "Assets:Cash"
SALES_ACCT = "Revenue:Sales"


def _w_csv(rows: Iterable[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    """Backward-compatible wrapper around :func:`ledgerloom.artifacts.write_csv_dicts`."""

    write_csv_dicts(path, rows, fieldnames=fieldnames)


def _w_json(obj: Any, path: Path) -> None:
    """Backward-compatible wrapper around :func:`ledgerloom.artifacts.write_json`."""

    write_json(path, obj)


def _make_entry(
    *,
    entry_id: str,
    dt: date,
    narration: str,
    lines: list[tuple[str, str, str]],
    meta: dict[str, Any] | None = None,
) -> Entry:
    postings: list[Posting] = []
    for acct, dr, cr in lines:
        postings.append(
            Posting(
                account=acct,
                debit=Decimal(dr),
                credit=Decimal(cr),
            )
        )
    m = {"entry_id": entry_id}
    if meta:
        m.update(meta)
    return Entry(dt=dt, narration=narration, postings=postings, meta=m)


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer: str
    invoice_date: date
    due_date: date
    amount_cents: int


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    customer: str
    receipt_date: date
    invoice_id: str
    amount_cents: int


def _cents_to_str(cents: int) -> str:
    return cents_to_str(cents)


def _str_to_cents(s: str) -> int:
    return str_to_cents(s)


def _trial_balance_from_postings(postings: pd.DataFrame) -> pd.DataFrame:
    return bookset.trial_balance(postings)


def _income_statement_from_tb(tb: pd.DataFrame) -> pd.DataFrame:
    return bookset.income_statement(tb)


def _balance_sheet_from_tb(tb: pd.DataFrame) -> pd.DataFrame:
    return bookset.balance_sheet_adjusted(tb)


def _df_to_csv(path: Path, df: pd.DataFrame) -> None:
    """Backward-compatible wrapper around :func:`ledgerloom.artifacts.write_csv_df`."""

    write_csv_df(path, df)


def _period_days_past_due(asof: date, due: date) -> int:
    return max(0, (asof - due).days)


def _aging_bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "Current"
    if days_past_due <= 30:
        return "1-30"
    if days_past_due <= 60:
        return "31-60"
    if days_past_due <= 90:
        return "61-90"
    return "90+"


def _gl_balance_cents(tb: pd.DataFrame, account: str) -> int:
    row = tb.loc[tb["account"] == account]
    if row.empty:
        return 0
    return _str_to_cents(str(row.iloc[0]["balance"]))


def run(outdir: Path, seed: int = 123) -> Path:
    """Run Chapter 09 and write artifacts. Returns the chapter output directory."""
    # seed is kept for CLI symmetry/determinism; this chapter uses fixed numbers.
    _ = seed

    cfg = LedgerEngineConfig()
    engine = LedgerEngine(cfg=cfg)

    # ------------------------------------------------------------------
    # 1) Start from Chapter 08 post-close, then create opening entry
    # ------------------------------------------------------------------
    close_date = PERIOD_START - timedelta(days=1)
    close_period = close_date.strftime("%Y-%m")
    snap = bookset.compute_post_close_snapshot(cfg=cfg, period=close_period, close_date=close_date)
    postings_post_close: pd.DataFrame = snap.postings_post_close
    tb_post_close: pd.DataFrame = snap.trial_balance_post_close

    # Keep the opening entry audit trail identical to the prior implementation:
    # meta.chapter remains "ch085" (this is a carry-forward artifact).
    opening_entry = bookset.compute_opening_from_post_close(
        tb_post_close=tb_post_close,
        opening_date=PERIOD_START,
        cfg=cfg,
        entry_id="OPEN-2026-02-01",
        narration="Opening balance carry-forward (from Ch08 post-close)",
        meta={"chapter": "ch085", "department": "HQ", "source": "ch08_post_close"},
    )

    postings_opening = engine.postings_fact_table([opening_entry])
    tb_opening = _trial_balance_from_postings(postings_opening)

    # Reconcile post-close TB (as-of last period) to opening TB (start of next period)
    recon_rows: list[dict[str, Any]] = []
    for acct in sorted(set(tb_post_close["account"]).union(set(tb_opening["account"]))):
        pc = _gl_balance_cents(tb_post_close, acct)
        op = _gl_balance_cents(tb_opening, acct)
        recon_rows.append(
            {
                "account": acct,
                "post_close_balance": _cents_to_str(pc),
                "opening_balance": _cents_to_str(op),
                "diff": _cents_to_str(op - pc),
            }
        )

    # ------------------------------------------------------------------
    # 2) A/R lifecycle events for the current period
    # ------------------------------------------------------------------
    invoices: list[Invoice] = [
        Invoice(
            invoice_id="INV-1001",
            customer="Acme Co",
            invoice_date=date(2026, 2, 3),
            due_date=date(2026, 3, 5),
            amount_cents=120_000,
        ),
        Invoice(
            invoice_id="INV-1002",
            customer="Beacon LLC",
            invoice_date=date(2026, 2, 15),
            due_date=date(2026, 3, 17),
            amount_cents=80_000,
        ),
    ]

    receipts: list[Receipt] = [
        Receipt(
            receipt_id="RCPT-2001",
            customer="Acme Co",
            receipt_date=date(2026, 2, 20),
            invoice_id="INV-1001",
            amount_cents=120_000,
        ),
        Receipt(
            receipt_id="RCPT-2002",
            customer="Beacon LLC",
            receipt_date=date(2026, 2, 25),
            invoice_id="INV-1002",
            amount_cents=30_000,
        ),
    ]

    ar_entries: list[Entry] = []

    for inv in invoices:
        amt = _cents_to_str(inv.amount_cents)
        ar_entries.append(
            _make_entry(
                entry_id=f"ar_invoice:{inv.invoice_id}",
                dt=inv.invoice_date,
                narration=f"Invoice {inv.invoice_id} to {inv.customer}",
                lines=[
                    (AR_ACCT, amt, "0.00"),
                    (SALES_ACCT, "0.00", amt),
                ],
                meta={
                    "event": "invoice",
                    "invoice_id": inv.invoice_id,
                    "customer": inv.customer,
                    "due_date": inv.due_date.isoformat(),
                },
            )
        )

    for r in receipts:
        amt = _cents_to_str(r.amount_cents)
        ar_entries.append(
            _make_entry(
                entry_id=f"ar_receipt:{r.receipt_id}",
                dt=r.receipt_date,
                narration=f"Cash receipt {r.receipt_id} from {r.customer} (applied to {r.invoice_id})",
                lines=[
                    (CASH_ACCT, amt, "0.00"),
                    (AR_ACCT, "0.00", amt),
                ],
                meta={
                    "event": "cash_receipt",
                    "receipt_id": r.receipt_id,
                    "invoice_id": r.invoice_id,
                    "customer": r.customer,
                },
            )
        )

    # ------------------------------------------------------------------
    # 3) Compute postings and derived reports
    # ------------------------------------------------------------------
    entries_all = [opening_entry] + ar_entries
    postings_all = engine.postings_fact_table(entries_all)

    # Split views for nicer learning artifacts.
    postings_ar = postings_all.loc[postings_all["entry_id"].astype(str).str.startswith("ar_")].copy()

    tb_end = _trial_balance_from_postings(postings_all)
    is_current = _income_statement_from_tb(tb_end)
    bs_current = _balance_sheet_from_tb(tb_end)

    gl_ar_end_cents = _gl_balance_cents(tb_end, AR_ACCT)

    # ------------------------------------------------------------------
    # 4) Build subledger (open items) + reconciliation
    # ------------------------------------------------------------------
    applied: dict[str, int] = {i.invoice_id: 0 for i in invoices}
    for r in receipts:
        applied[r.invoice_id] = applied.get(r.invoice_id, 0) + r.amount_cents

    open_items_rows: list[dict[str, Any]] = []
    open_total_cents = 0
    for inv in invoices:
        paid = applied.get(inv.invoice_id, 0)
        open_cents = inv.amount_cents - paid
        open_total_cents += open_cents
        dpp = _period_days_past_due(PERIOD_END, inv.due_date)
        open_items_rows.append(
            {
                "invoice_id": inv.invoice_id,
                "customer": inv.customer,
                "invoice_date": inv.invoice_date.isoformat(),
                "due_date": inv.due_date.isoformat(),
                "invoice_amount": _cents_to_str(inv.amount_cents),
                "cash_applied": _cents_to_str(paid),
                "open_balance": _cents_to_str(open_cents),
                "days_past_due": dpp,
                "aging_bucket": _aging_bucket(dpp),
            }
        )

    reconciliation_rows = [
        {
            "asof": PERIOD_END.isoformat(),
            "gl_ar_control_balance": _cents_to_str(gl_ar_end_cents),
            "subledger_open_items_total": _cents_to_str(open_total_cents),
            "diff": _cents_to_str(gl_ar_end_cents - open_total_cents),
        }
    ]

    # ------------------------------------------------------------------
    # 5) Write artifacts
    # ------------------------------------------------------------------
    out_ch = outdir / CHAPTER
    out_ch.mkdir(parents=True, exist_ok=True)

    # Source continuity artifacts
    _df_to_csv(out_ch / "postings_post_close.csv", postings_post_close)
    _df_to_csv(out_ch / "trial_balance_post_close.csv", tb_post_close)

    _df_to_csv(out_ch / "postings_opening.csv", postings_opening)
    _df_to_csv(out_ch / "trial_balance_opening.csv", tb_opening)
    _w_csv(recon_rows, out_ch / "reconciliation_post_close_vs_opening.csv", [
        "account",
        "post_close_balance",
        "opening_balance",
 "diff",
    ])

    # Operational artifacts
    _w_csv(
        [
            {
                "invoice_id": i.invoice_id,
                "customer": i.customer,
                "invoice_date": i.invoice_date.isoformat(),
                "due_date": i.due_date.isoformat(),
                "amount": _cents_to_str(i.amount_cents),
            }
            for i in invoices
        ],
        out_ch / "invoices_register.csv",
        ["invoice_id", "customer", "invoice_date", "due_date", "amount"],
    )

    _w_csv(
        [
            {
                "receipt_id": r.receipt_id,
                "customer": r.customer,
                "receipt_date": r.receipt_date.isoformat(),
                "invoice_id": r.invoice_id,
                "amount": _cents_to_str(r.amount_cents),
            }
            for r in receipts
        ],
        out_ch / "cash_receipts_register.csv",
        ["receipt_id", "customer", "receipt_date", "invoice_id", "amount"],
    )

    _df_to_csv(out_ch / "postings_ar.csv", postings_ar)

    _w_csv(
        open_items_rows,
        out_ch / "ar_open_items.csv",
        [
            "invoice_id",
            "customer",
            "invoice_date",
            "due_date",
            "invoice_amount",
            "cash_applied",
            "open_balance",
            "days_past_due",
            "aging_bucket",
        ],
    )

    _w_csv(
        reconciliation_rows,
        out_ch / "ar_control_reconciliation.csv",
        ["asof", "gl_ar_control_balance", "subledger_open_items_total", "diff"],
    )

    _df_to_csv(out_ch / "trial_balance_end_period.csv", tb_end)
    _df_to_csv(out_ch / "income_statement_current_period.csv", is_current)
    _df_to_csv(out_ch / "balance_sheet_current_period.csv", bs_current)

    # Engine invariants + custom reconciliation checks
    inv = engine.invariants(entries_all, postings_all)
    inv["checks"] = {
        "reconcile_ar_control_to_subledger": {
            "ok": gl_ar_end_cents == open_total_cents,
            "gl_ar_control_balance": _cents_to_str(gl_ar_end_cents),
            "subledger_total": _cents_to_str(open_total_cents),
        },
        "open_items_non_negative": {
            "ok": all(_str_to_cents(r["open_balance"]) >= 0 for r in open_items_rows),
        },
    }
    _w_json(inv, out_ch / "invariants.json")

    checklist = {
        "chapter": CHAPTER,
        "period_start": PERIOD_START.isoformat(),
        "period_end": PERIOD_END.isoformat(),
        "has_opening_entry": True,
        "invoices_count": len(invoices),
        "receipts_count": len(receipts),
        "ar_control_equals_subledger": gl_ar_end_cents == open_total_cents,
    }
    _w_json(checklist, out_ch / "ar_checklist.json")

    artifact_names = [
        "postings_opening.csv",
        "postings_ar.csv",
        "invoices_register.csv",
        "cash_receipts_register.csv",
        "ar_open_items.csv",
        "trial_balance_opening.csv",
        "trial_balance_end_period.csv",
        "income_statement_current_period.csv",
        "balance_sheet_current_period.csv",
        "invariants.json",
        "ar_control_reconciliation.csv",
        "postings_post_close.csv",
        "trial_balance_post_close.csv",
        "reconciliation_post_close_vs_opening.csv",
    ]

    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        'chapter': CHAPTER,
        'module': 'ledgerloom.chapters.ch09_ar_lifecycle',
        'seed': seed,
        'period_start': PERIOD_START.isoformat(),
        'period_end': PERIOD_END.isoformat(),
    }

    def _manifest_payload(d: Path) -> dict[str, Any]:
        names = list(artifact_names) + ['run_meta.json']
        return {
            'chapter': CHAPTER,
            'artifacts': artifacts_map(d, names),
            'notes': {'line_endings': 'LF', 'seed': seed},
        }

    emit_trust_artifacts(out_ch, run_meta=run_meta, manifest=_manifest_payload)

    return out_ch


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--seed", type=int, default=123)
    args = p.parse_args(argv)

    ch_dir = run(args.outdir, seed=args.seed)
    print(f"Wrote LedgerLoom Chapter 09 artifacts -> {ch_dir}")


if __name__ == "__main__":
    main()

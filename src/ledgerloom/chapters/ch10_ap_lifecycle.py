"""LedgerLoom Chapter 10: Accounts Payable lifecycle (control + subledger).

This chapter mirrors Chapter 09 (A/R) but for Accounts Payable.

We start from Chapter 08 post-close balances, create an opening entry for the
next period (same concept as Chapter 08.5), then run a tiny A/P cycle:

- Record vendor bills (A/P control increases)
- Record a vendor credit memo (A/P control decreases + reverses expense)
- Pay vendors and apply payments to bills (A/P control decreases)
- Build an A/P open-items subledger and aging snapshot
- Reconcile subledger total to the A/P control account in the G/L

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


CHAPTER = "ch10"
PERIOD_START = date(2026, 2, 1)
PERIOD_END = date(2026, 2, 28)

AP_ACCT = "Liabilities:AccountsPayable"
CASH_ACCT = "Assets:Cash"
UTILITIES_ACCT = "Expenses:Utilities"
SUPPLIES_ACCT = "Expenses:Supplies"


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
class Bill:
    bill_id: str
    vendor: str
    bill_date: date
    due_date: date
    amount_cents: int
    expense_account: str
    approved_by: str
    approved_at: date | None
    po_number: str


@dataclass(frozen=True)
class VendorCredit:
    credit_id: str
    vendor: str
    credit_date: date
    bill_id: str
    amount_cents: int
    reason: str


@dataclass(frozen=True)
class Payment:
    payment_id: str
    vendor: str
    payment_date: date
    bill_id: str
    amount_cents: int
    method: str



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
    # 2) A/P lifecycle events for the current period
    # ------------------------------------------------------------------

    bills: list[Bill] = [
        Bill(
            bill_id="BILL-1001",
            vendor="BC Hydro",
            bill_date=date(2026, 2, 3),
            due_date=date(2026, 3, 5),
            amount_cents=120_000,
            expense_account=UTILITIES_ACCT,
            approved_by="ap_mgr",
            approved_at=date(2026, 2, 4),
            po_number="PO-2026-0203",
        ),
        # Intentionally unapproved (teachable control weakness): appears in the
        # open-items report and is past due at period end.
        Bill(
            bill_id="BILL-1002",
            vendor="Beacon Office Supply",
            bill_date=date(2026, 2, 15),
            due_date=date(2026, 2, 23),
            amount_cents=80_000,
            expense_account=SUPPLIES_ACCT,
            approved_by="",
            approved_at=None,
            po_number="",
        ),
    ]

    credits: list[VendorCredit] = [
        VendorCredit(
            credit_id="CR-2001",
            vendor="Beacon Office Supply",
            credit_date=date(2026, 2, 18),
            bill_id="BILL-1002",
            amount_cents=5_000,
            reason="Return credit memo",
        )
    ]

    payments: list[Payment] = [
        Payment(
            payment_id="PAY-3001",
            vendor="BC Hydro",
            payment_date=date(2026, 2, 20),
            bill_id="BILL-1001",
            amount_cents=120_000,
            method="ACH",
        ),
        Payment(
            payment_id="PAY-3002",
            vendor="Beacon Office Supply",
            payment_date=date(2026, 2, 25),
            bill_id="BILL-1002",
            amount_cents=30_000,
            method="Check",
        ),
    ]

    ap_entries: list[Entry] = []

    for b in bills:
        amt = _cents_to_str(b.amount_cents)
        ap_entries.append(
            _make_entry(
                entry_id=f"ap_bill:{b.bill_id}",
                dt=b.bill_date,
                narration=f"Vendor bill {b.bill_id} from {b.vendor}",
                lines=[
                    (b.expense_account, amt, "0.00"),
                    (AP_ACCT, "0.00", amt),
                ],
                meta={
                    "event": "vendor_bill",
                    "bill_id": b.bill_id,
                    "vendor": b.vendor,
                    "due_date": b.due_date.isoformat(),
                    "approved_by": b.approved_by,
                    "approved_at": b.approved_at.isoformat() if b.approved_at else "",
                    "po_number": b.po_number,
                },
            )
        )

    for c in credits:
        amt = _cents_to_str(c.amount_cents)
        # Credit memo reverses the original expense: debit A/P, credit expense.
        bill = next((b for b in bills if b.bill_id == c.bill_id), None)
        if bill is None:
            raise ValueError(f"Unknown bill_id for credit memo: {c.bill_id}")
        ap_entries.append(
            _make_entry(
                entry_id=f"ap_credit:{c.credit_id}",
                dt=c.credit_date,
                narration=f"Vendor credit {c.credit_id} from {c.vendor} (applied to {c.bill_id})",
                lines=[
                    (AP_ACCT, amt, "0.00"),
                    (bill.expense_account, "0.00", amt),
                ],
                meta={
                    "event": "vendor_credit",
                    "credit_id": c.credit_id,
                    "bill_id": c.bill_id,
                    "vendor": c.vendor,
                    "reason": c.reason,
                },
            )
        )

    for pay in payments:
        amt = _cents_to_str(pay.amount_cents)
        ap_entries.append(
            _make_entry(
                entry_id=f"ap_payment:{pay.payment_id}",
                dt=pay.payment_date,
                narration=f"Vendor payment {pay.payment_id} to {pay.vendor} (applied to {pay.bill_id})",
                lines=[
                    (AP_ACCT, amt, "0.00"),
                    (CASH_ACCT, "0.00", amt),
                ],
                meta={
                    "event": "payment",
                    "payment_id": pay.payment_id,
                    "bill_id": pay.bill_id,
                    "vendor": pay.vendor,
                    "method": pay.method,
                },
            )
        )

    # ------------------------------------------------------------------
    # 3) Compute postings and derived reports
    # ------------------------------------------------------------------
    entries_all = [opening_entry] + ap_entries
    postings_all = engine.postings_fact_table(entries_all)

    # Split views for nicer learning artifacts.
    postings_ap = postings_all.loc[postings_all["entry_id"].astype(str).str.startswith("ap_")].copy()

    tb_end = _trial_balance_from_postings(postings_all)
    is_current = _income_statement_from_tb(tb_end)
    bs_current = _balance_sheet_from_tb(tb_end)

    gl_ap_end_cents = _gl_balance_cents(tb_end, AP_ACCT)

    # ------------------------------------------------------------------
    # 4) Build subledger (open items) + reconciliation
    # ------------------------------------------------------------------
    payments_applied: dict[str, int] = {b.bill_id: 0 for b in bills}
    for pay in payments:
        payments_applied[pay.bill_id] = payments_applied.get(pay.bill_id, 0) + pay.amount_cents

    credits_applied: dict[str, int] = {b.bill_id: 0 for b in bills}
    for c in credits:
        credits_applied[c.bill_id] = credits_applied.get(c.bill_id, 0) + c.amount_cents

    open_items_rows: list[dict[str, Any]] = []
    open_total_cents = 0
    all_approved = True

    for b in bills:
        paid = payments_applied.get(b.bill_id, 0)
        credited = credits_applied.get(b.bill_id, 0)
        open_cents = b.amount_cents - paid - credited
        open_total_cents += open_cents

        dpp = _period_days_past_due(PERIOD_END, b.due_date)
        approved = bool(b.approved_by) and b.approved_at is not None
        all_approved = all_approved and approved

        open_items_rows.append(
            {
                "bill_id": b.bill_id,
                "vendor": b.vendor,
                "bill_date": b.bill_date.isoformat(),
                "due_date": b.due_date.isoformat(),
                "bill_amount": _cents_to_str(b.amount_cents),
                "payments_applied": _cents_to_str(paid),
                "credits_applied": _cents_to_str(credited),
                "open_balance": _cents_to_str(open_cents),
                "days_past_due": dpp,
                "aging_bucket": _aging_bucket(dpp),
                "approved": "true" if approved else "false",
            }
        )

    reconciliation_rows = [
        {
            "asof": PERIOD_END.isoformat(),
            "gl_ap_control_balance": _cents_to_str(gl_ap_end_cents),
            "subledger_open_items_total": _cents_to_str(open_total_cents),
            "diff": _cents_to_str(gl_ap_end_cents - open_total_cents),
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
    _w_csv(
        recon_rows,
        out_ch / "reconciliation_post_close_vs_opening.csv",
        [
            "account",
            "post_close_balance",
            "opening_balance",
            "diff",
        ],
    )

    # Operational artifacts
    _w_csv(
        [
            {
                "bill_id": b.bill_id,
                "vendor": b.vendor,
                "bill_date": b.bill_date.isoformat(),
                "due_date": b.due_date.isoformat(),
                "amount": _cents_to_str(b.amount_cents),
                "approved_by": b.approved_by,
                "approved_at": b.approved_at.isoformat() if b.approved_at else "",
                "po_number": b.po_number,
            }
            for b in bills
        ],
        out_ch / "vendor_bills_register.csv",
        [
            "bill_id",
            "vendor",
            "bill_date",
            "due_date",
            "amount",
            "approved_by",
            "approved_at",
            "po_number",
        ],
    )

    _w_csv(
        [
            {
                "credit_id": c.credit_id,
                "vendor": c.vendor,
                "credit_date": c.credit_date.isoformat(),
                "bill_id": c.bill_id,
                "amount": _cents_to_str(c.amount_cents),
                "reason": c.reason,
            }
            for c in credits
        ],
        out_ch / "vendor_credits_register.csv",
        [
            "credit_id",
            "vendor",
            "credit_date",
            "bill_id",
            "amount",
            "reason",
        ],
    )

    _w_csv(
        [
            {
                "payment_id": pay.payment_id,
                "vendor": pay.vendor,
                "payment_date": pay.payment_date.isoformat(),
                "bill_id": pay.bill_id,
                "amount": _cents_to_str(pay.amount_cents),
                "method": pay.method,
            }
            for pay in payments
        ],
        out_ch / "cash_disbursements_register.csv",
        [
            "payment_id",
            "vendor",
            "payment_date",
            "bill_id",
            "amount",
            "method",
        ],
    )

    _df_to_csv(out_ch / "postings_ap.csv", postings_ap)

    _w_csv(
        open_items_rows,
        out_ch / "ap_open_items.csv",
        [
            "bill_id",
            "vendor",
            "bill_date",
            "due_date",
            "bill_amount",
            "payments_applied",
            "credits_applied",
            "open_balance",
            "days_past_due",
            "aging_bucket",
            "approved",
        ],
    )

    _w_csv(
        reconciliation_rows,
        out_ch / "ap_control_reconciliation.csv",
        ["asof", "gl_ap_control_balance", "subledger_open_items_total", "diff"],
    )

    _df_to_csv(out_ch / "trial_balance_end_period.csv", tb_end)
    _df_to_csv(out_ch / "income_statement_current_period.csv", is_current)
    _df_to_csv(out_ch / "balance_sheet_current_period.csv", bs_current)

    # Engine invariants + custom reconciliation checks
    inv = engine.invariants(entries_all, postings_all)
    inv["checks"] = {
        "reconcile_ap_control_to_subledger": {
            "ok": gl_ap_end_cents == open_total_cents,
            "gl_ap_control_balance": _cents_to_str(gl_ap_end_cents),
            "subledger_total": _cents_to_str(open_total_cents),
        },
        "open_items_non_negative": {
            "ok": all(_str_to_cents(r["open_balance"]) >= 0 for r in open_items_rows),
        },
        "all_bills_approved": {
            "ok": all_approved,
            "unapproved_bill_ids": [r["bill_id"] for r in open_items_rows if r["approved"] != "true"],
        },
    }
    _w_json(inv, out_ch / "invariants.json")

    checklist = {
        "chapter": CHAPTER,
        "period_start": PERIOD_START.isoformat(),
        "period_end": PERIOD_END.isoformat(),
        "has_opening_entry": True,
        "bills_count": len(bills),
        "vendor_credits_count": len(credits),
        "payments_count": len(payments),
        "ap_control_equals_subledger": gl_ap_end_cents == open_total_cents,
        "all_bills_approved": all_approved,
    }
    _w_json(checklist, out_ch / "ap_checklist.json")

    artifact_names = [
        "trial_balance_opening.csv",
        "postings_opening.csv",
        "postings_post_close.csv",
        "trial_balance_post_close.csv",
        "reconciliation_post_close_vs_opening.csv",
        "vendor_bills_register.csv",
        "vendor_credits_register.csv",
        "cash_disbursements_register.csv",
        "postings_ap.csv",
        "ap_open_items.csv",
        "ap_control_reconciliation.csv",
        "trial_balance_end_period.csv",
        "income_statement_current_period.csv",
        "balance_sheet_current_period.csv",
        "invariants.json",
        "ap_checklist.json",
    ]
    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        'chapter': CHAPTER,
        'module': 'ledgerloom.chapters.ch10_ap_lifecycle',
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
    print(f"Wrote LedgerLoom Chapter 10 artifacts -> {ch_dir}")


if __name__ == "__main__":
    main()

"""LedgerLoom Chapter 11: Inventory and COGS (simple perpetual costing).

This chapter introduces **inventory** as an operational subsystem and shows how
to connect inventory movements to **Cost of Goods Sold (COGS)**.

Key ideas
---------
- **Perpetual vs periodic**: perpetual updates inventory + COGS on each sale;
  periodic estimates COGS from (Begin Inv + Purchases - End Inv).
- Inventory movements as events: purchases (receipts), sales (issues), and
  adjustments (cycle counts / shrink).
- A simple costing assumption: **moving average cost** per SKU.
- A control pattern: reconcile the inventory subledger valuation to the
  ``Assets:Inventory`` control balance in the G/L.

The goal is clarity, determinism, and testability — not a full ERP.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ledgerloom.artifacts import artifacts_map, write_csv_df, write_csv_dicts, write_json
from ledgerloom.trust.pipeline import emit_trust_artifacts
from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine
from ledgerloom.engine.config import LedgerEngineConfig
from ledgerloom.engine.money import cents_to_str, str_to_cents
from ledgerloom.scenarios import bookset_v1 as bookset

CHAPTER = "ch11"
PERIOD_START = date(2026, 2, 1)
ASOF_DATE = date(2026, 2, 28)

SKU = "WIDGET-A"


@dataclass(frozen=True)
class InventoryMovement:
    movement_id: str
    movement_date: date
    sku: str
    movement_type: str  # purchase_receipt | sale_issue | shrink_adjustment
    qty_in: int
    qty_out: int
    unit_cost_cents: int
    source_doc_id: str
    sale_id: str | None = None


@dataclass(frozen=True)
class Sale:
    sale_id: str
    sale_date: date
    sku: str
    quantity: int
    unit_price_cents: int


def _cents(c: int) -> Decimal:
    return Decimal(cents_to_str(c))


def _tb(postings: pd.DataFrame) -> pd.DataFrame:
    return bookset.trial_balance(postings)


def _is(tb: pd.DataFrame) -> pd.DataFrame:
    return bookset.income_statement(tb)


def _bs(tb: pd.DataFrame) -> pd.DataFrame:
    return bookset.balance_sheet_adjusted(tb)


def _w_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    write_csv_dicts(path, rows, fieldnames=fieldnames)


def _w_df(path: Path, df: pd.DataFrame) -> None:
    write_csv_df(path, df)


def _w_json(path: Path, payload: Any) -> None:
    write_json(path, payload)


def _gl_balance_cents(tb: pd.DataFrame, account: str) -> int:
    row = tb.loc[tb["account"] == account]
    if row.empty:
        return 0
    return int(round(float(row.iloc[0]["balance"]) * 100))


def _make_entry(entry_id: str, dt: date, narration: str, postings: list[Posting], meta: dict[str, Any]) -> Entry:
    m = {"entry_id": entry_id, "chapter": CHAPTER, **meta}
    return Entry(dt=dt, narration=narration, postings=postings, meta=m)


def _inventory_dataset() -> tuple[list[InventoryMovement], list[Sale]]:
    # Purchases: paid cash (keeps Chapter 11 focused on Inventory/COGS)
    purchases = [
        InventoryMovement(
            movement_id="MOV-1001",
            movement_date=date(2026, 2, 2),
            sku=SKU,
            movement_type="purchase_receipt",
            qty_in=100,
            qty_out=0,
            unit_cost_cents=1000,
            source_doc_id="PO-4001",
        ),
        InventoryMovement(
            movement_id="MOV-1002",
            movement_date=date(2026, 2, 10),
            sku=SKU,
            movement_type="purchase_receipt",
            qty_in=60,
            qty_out=0,
            unit_cost_cents=1200,
            source_doc_id="PO-4002",
        ),
    ]

    sales = [
        Sale(
            sale_id="SALE-5001",
            sale_date=date(2026, 2, 12),
            sku=SKU,
            quantity=80,
            unit_price_cents=2000,
        ),
        Sale(
            sale_id="SALE-5002",
            sale_date=date(2026, 2, 20),
            sku=SKU,
            quantity=30,
            unit_price_cents=2000,
        ),
    ]

    # Placeholder movements for sales (unit_cost computed during valuation)
    sale_moves = [
        InventoryMovement(
            movement_id="MOV-2001",
            movement_date=sales[0].sale_date,
            sku=sales[0].sku,
            movement_type="sale_issue",
            qty_in=0,
            qty_out=sales[0].quantity,
            unit_cost_cents=0,
            source_doc_id="INV-5001",
            sale_id=sales[0].sale_id,
        ),
        InventoryMovement(
            movement_id="MOV-2002",
            movement_date=sales[1].sale_date,
            sku=sales[1].sku,
            movement_type="sale_issue",
            qty_in=0,
            qty_out=sales[1].quantity,
            unit_cost_cents=0,
            source_doc_id="INV-5002",
            sale_id=sales[1].sale_id,
        ),
    ]

    # Shrink adjustment at month-end (cycle count)
    shrink = InventoryMovement(
        movement_id="MOV-3001",
        movement_date=date(2026, 2, 28),
        sku=SKU,
        movement_type="shrink_adjustment",
        qty_in=0,
        qty_out=2,
        unit_cost_cents=0,  # computed using current moving average
        source_doc_id="COUNT-2026-02",
    )

    movements = sorted([*purchases, *sale_moves, shrink], key=lambda m: (m.movement_date, m.movement_id))
    return movements, sales


def _apply_moving_average(movements: list[InventoryMovement]) -> tuple[list[InventoryMovement], dict[str, Any]]:
    """Compute moving-average unit costs for issues/adjustments.

    Returns:
        (movements_with_costs, summary)
    """
    on_hand_qty = 0
    total_cost_cents = 0

    out: list[InventoryMovement] = []
    cogs_by_sale: dict[str, int] = {}
    unit_cost_by_sale: dict[str, int] = {}
    shrink_cost_cents = 0

    for m in movements:
        if m.movement_type == "purchase_receipt":
            ext = m.qty_in * m.unit_cost_cents
            on_hand_qty += m.qty_in
            total_cost_cents += ext
            out.append(m)
            continue

        if on_hand_qty <= 0:
            raise ValueError(f"Inventory on-hand is zero/negative before movement {m.movement_id}")

        # Integer cents moving average (dataset constructed to be exact)
        avg_unit_cost = total_cost_cents // on_hand_qty

        if m.movement_type in {"sale_issue", "shrink_adjustment"}:
            ext = m.qty_out * avg_unit_cost
            on_hand_qty -= m.qty_out
            total_cost_cents -= ext

            m2 = InventoryMovement(
                **{**m.__dict__, "unit_cost_cents": avg_unit_cost}
            )
            out.append(m2)

            if m.movement_type == "sale_issue":
                assert m.sale_id is not None
                cogs_by_sale[m.sale_id] = cogs_by_sale.get(m.sale_id, 0) + ext
                unit_cost_by_sale[m.sale_id] = avg_unit_cost
            else:
                shrink_cost_cents += ext
            continue

        raise ValueError(f"Unknown movement_type: {m.movement_type}")

    summary = {
        "sku": SKU,
        "ending_qty": on_hand_qty,
        "ending_value_cents": total_cost_cents,
        "avg_unit_cost_cents_end": (total_cost_cents // on_hand_qty) if on_hand_qty else 0,
        "cogs_by_sale_cents": cogs_by_sale,
        "unit_cost_by_sale_cents": unit_cost_by_sale,
        "shrink_cost_cents": shrink_cost_cents,
    }
    return out, summary


def run(outdir: Path, seed: int = 123) -> Path:
    _ = seed  # deterministic chapter; seed kept for CLI consistency

    cfg = LedgerEngineConfig()
    engine = LedgerEngine(cfg=cfg)

    out_ch = outdir / CHAPTER
    out_ch.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1) Start from Chapter 08 post-close, then create opening entry
    # ------------------------------------------------------------------
    close_date = PERIOD_START - timedelta(days=1)
    close_period = close_date.strftime("%Y-%m")
    snap = bookset.compute_post_close_snapshot(cfg=cfg, period=close_period, close_date=close_date)
    postings_post_close: pd.DataFrame = snap.postings_post_close
    tb_post_close: pd.DataFrame = snap.trial_balance_post_close

    opening_entry = bookset.compute_opening_from_post_close(
        tb_post_close=tb_post_close,
        opening_date=PERIOD_START,
        cfg=cfg,
        entry_id="OPEN-2026-02-01",
        narration="Opening balance carry-forward (from Ch08 post-close)",
        meta={"chapter": "ch085", "department": "HQ", "source": "ch08_post_close"},
    )

    postings_opening = engine.postings_fact_table([opening_entry])
    tb_opening = _tb(postings_opening)

    # Reconcile post-close TB (as-of last period) to opening TB (start of next period)
    recon_rows: list[dict[str, Any]] = []
    for acct in sorted(set(tb_post_close["account"]).union(set(tb_opening["account"]))):
        a = tb_post_close.loc[tb_post_close["account"] == acct, "balance"]
        b = tb_opening.loc[tb_opening["account"] == acct, "balance"]
        post_close = float(a.iloc[0]) if not a.empty else 0.0
        opening = float(b.iloc[0]) if not b.empty else 0.0
        recon_rows.append(
            {"account": acct, "post_close_balance": post_close, "opening_balance": opening, "diff": opening - post_close}
        )
    recon_df = pd.DataFrame(recon_rows)

    # ------------------------------------------------------------------
    # 2) Inventory movements + sales events (moving-average cost)
    # ------------------------------------------------------------------
    movements_raw, sales = _inventory_dataset()
    movements, inv_summary = _apply_moving_average(movements_raw)

    # Registers (human-readable; computed values embedded)
    movement_rows: list[dict[str, Any]] = []
    for m in movements:
        ext_cents = (m.qty_in * m.unit_cost_cents) if m.qty_in else (m.qty_out * m.unit_cost_cents)
        movement_rows.append(
            {
                "movement_id": m.movement_id,
                "movement_date": m.movement_date.isoformat(),
                "sku": m.sku,
                "movement_type": m.movement_type,
                "qty_in": m.qty_in,
                "qty_out": m.qty_out,
                "unit_cost": cents_to_str(m.unit_cost_cents),
                "extended_cost": cents_to_str(ext_cents),
                "source_doc_id": m.source_doc_id,
                "sale_id": m.sale_id or "",
            }
        )

    sales_rows: list[dict[str, Any]] = []
    for s in sales:
        sales_rows.append(
            {
                "sale_id": s.sale_id,
                "sale_date": s.sale_date.isoformat(),
                "sku": s.sku,
                "quantity": s.quantity,
                "unit_price": cents_to_str(s.unit_price_cents),
                "revenue_amount": cents_to_str(s.quantity * s.unit_price_cents),
            }
        )

    cogs_rows: list[dict[str, Any]] = []
    for s in sales:
        cogs_cents = int(inv_summary["cogs_by_sale_cents"][s.sale_id])
        unit_cost_cents = int(inv_summary["unit_cost_by_sale_cents"][s.sale_id])
        cogs_rows.append(
            {
                "sale_id": s.sale_id,
                "sku": s.sku,
                "quantity": s.quantity,
                "unit_cost": cents_to_str(unit_cost_cents),
                "cogs_amount": cents_to_str(cogs_cents),
            }
        )

    valuation_rows = [
        {
            "sku": SKU,
            "on_hand_qty": int(inv_summary["ending_qty"]),
            "avg_unit_cost": cents_to_str(int(inv_summary["avg_unit_cost_cents_end"])),
            "inventory_value": cents_to_str(int(inv_summary["ending_value_cents"])),
        }
    ]

    checklist = {
        "chapter": CHAPTER,
        "asof": ASOF_DATE.isoformat(),
        "costing_method": "moving_average",
        "sku": SKU,
        "purchase_count": len([m for m in movements if m.movement_type == "purchase_receipt"]),
        "sale_count": len([m for m in movements if m.movement_type == "sale_issue"]),
        "ending_on_hand_qty": int(inv_summary["ending_qty"]),
        "limitations": [
            "Single SKU example (extend to multiple SKUs by keying state per SKU).",
            "Moving-average cost ignores lot tracking and exact FIFO/LIFO layers.",
            "No backdated receipts or returns in this minimal dataset.",
        ],
    }

    # ------------------------------------------------------------------
    # 3) Translate movements into G/L entries
    # ------------------------------------------------------------------
    entries_new: list[Entry] = []

    # Purchases: Dr Inventory, Cr Cash
    for m in movements:
        if m.movement_type != "purchase_receipt":
            continue
        cost_cents = m.qty_in * m.unit_cost_cents
        entries_new.append(
            _make_entry(
                entry_id=f"inv_purchase:{m.source_doc_id}",
                dt=m.movement_date,
                narration=f"Inventory purchase receipt {m.source_doc_id} ({m.qty_in} units)",
                postings=[
                    Posting(account="Assets:Inventory", debit=_cents(cost_cents)),
                    Posting(account="Assets:Cash", credit=_cents(cost_cents)),
                ],
                meta={"entry_kind": "purchase", "source_doc_id": m.source_doc_id},
            )
        )

    # Sales: Dr Cash, Cr Revenue; Dr COGS, Cr Inventory
    sale_lookup = {s.sale_id: s for s in sales}
    for m in movements:
        if m.movement_type != "sale_issue":
            continue
        assert m.sale_id is not None
        s = sale_lookup[m.sale_id]
        revenue_cents = s.quantity * s.unit_price_cents
        cogs_cents = s.quantity * m.unit_cost_cents
        entries_new.append(
            _make_entry(
                entry_id=f"inv_sale:{s.sale_id}",
                dt=s.sale_date,
                narration=f"Sale {s.sale_id} ({s.quantity} units) with COGS",
                postings=[
                    Posting(account="Assets:Cash", debit=_cents(revenue_cents)),
                    Posting(account="Revenue:Sales", credit=_cents(revenue_cents)),
                    Posting(account="Expenses:COGS", debit=_cents(cogs_cents)),
                    Posting(account="Assets:Inventory", credit=_cents(cogs_cents)),
                ],
                meta={"entry_kind": "sale", "sale_id": s.sale_id},
            )
        )

    # Shrink adjustment: Dr InventoryShrinkage, Cr Inventory
    for m in movements:
        if m.movement_type != "shrink_adjustment":
            continue
        cost_cents = m.qty_out * m.unit_cost_cents
        entries_new.append(
            _make_entry(
                entry_id=f"inv_adjust:{m.source_doc_id}",
                dt=m.movement_date,
                narration=f"Inventory shrink (cycle count) {m.source_doc_id}",
                postings=[
                    Posting(account="Expenses:InventoryShrinkage", debit=_cents(cost_cents)),
                    Posting(account="Assets:Inventory", credit=_cents(cost_cents)),
                ],
                meta={"entry_kind": "adjustment", "source_doc_id": m.source_doc_id},
            )
        )

    entries_all = [opening_entry, *entries_new]
    postings_all = engine.postings_fact_table(entries_all)

    # Chapter-level subset: only the inventory + COGS entries (exclude opening)
    inv_entry_ids = {e.meta["entry_id"] for e in entries_new}
    postings_inv = postings_all.loc[postings_all["entry_id"].isin(sorted(inv_entry_ids))].copy()

    tb_end = _tb(postings_all)
    is_current = _is(tb_end)
    bs_current = _bs(tb_end)

    gl_inv_cents = _gl_balance_cents(tb_end, "Assets:Inventory")
    subledger_inv_cents = int(inv_summary["ending_value_cents"])

    recon_control = pd.DataFrame(
        [
            {
                "asof": ASOF_DATE.isoformat(),
                "gl_inventory_balance": cents_to_str(gl_inv_cents),
                "subledger_inventory_value": cents_to_str(subledger_inv_cents),
                "diff": cents_to_str(gl_inv_cents - subledger_inv_cents),
            }
        ]
    )

    # Engine invariants + custom checks
    inv = engine.invariants(entries_all, postings_all)
    inv["checks"] = {
        "inventory_control_reconciles": {
            "ok": gl_inv_cents == subledger_inv_cents,
            "gl_inventory_balance": cents_to_str(gl_inv_cents),
            "subledger_inventory_value": cents_to_str(subledger_inv_cents),
        },
        "inventory_non_negative": {
            "ok": int(inv_summary["ending_qty"]) >= 0,
            "ending_qty": int(inv_summary["ending_qty"]),
        },
        "cogs_links_to_sales": {
            "ok": sum(inv_summary["cogs_by_sale_cents"].values()) == sum(
                str_to_cents(r["cogs_amount"]) for r in cogs_rows
            ),
        },
    }

    # ------------------------------------------------------------------
    # 4) Write artifacts + manifest
    # ------------------------------------------------------------------
    _w_df(out_ch / "postings_post_close.csv", postings_post_close)
    _w_df(out_ch / "trial_balance_post_close.csv", tb_post_close)
    _w_df(out_ch / "postings_opening.csv", postings_opening)
    _w_df(out_ch / "trial_balance_opening.csv", tb_opening)
    _w_df(out_ch / "reconciliation_post_close_vs_opening.csv", recon_df)

    _w_csv(
        out_ch / "inventory_movements.csv",
        movement_rows,
        fieldnames=[
            "movement_id",
            "movement_date",
            "sku",
            "movement_type",
            "qty_in",
            "qty_out",
            "unit_cost",
            "extended_cost",
            "source_doc_id",
            "sale_id",
        ],
    )
    _w_csv(
        out_ch / "sales_register.csv",
        sales_rows,
        fieldnames=["sale_id", "sale_date", "sku", "quantity", "unit_price", "revenue_amount"],
    )
    _w_csv(
        out_ch / "cogs_by_sale.csv",
        cogs_rows,
        fieldnames=["sale_id", "sku", "quantity", "unit_cost", "cogs_amount"],
    )
    _w_csv(
        out_ch / "inventory_valuation_end_period.csv",
        valuation_rows,
        fieldnames=["sku", "on_hand_qty", "avg_unit_cost", "inventory_value"],
    )
    _w_df(out_ch / "inventory_control_reconciliation.csv", recon_control)

    _w_df(out_ch / "postings_inventory_cogs.csv", postings_inv)
    _w_df(out_ch / "trial_balance_end_period.csv", tb_end)
    _w_df(out_ch / "income_statement_current_period.csv", is_current)
    _w_df(out_ch / "balance_sheet_current_period.csv", bs_current)

    _w_json(out_ch / "invariants.json", inv)
    _w_json(out_ch / "inventory_checklist.json", checklist)

    artifact_names = [
        "postings_post_close.csv",
        "trial_balance_post_close.csv",
        "postings_opening.csv",
        "trial_balance_opening.csv",
        "reconciliation_post_close_vs_opening.csv",
        "inventory_movements.csv",
        "sales_register.csv",
        "cogs_by_sale.csv",
        "inventory_valuation_end_period.csv",
        "inventory_control_reconciliation.csv",
        "postings_inventory_cogs.csv",
        "trial_balance_end_period.csv",
        "income_statement_current_period.csv",
        "balance_sheet_current_period.csv",
        "invariants.json",
        "inventory_checklist.json",
    ]
    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        'chapter': CHAPTER,
        'module': 'ledgerloom.chapters.ch11_inventory_cogs',
        'seed': seed,
        'period_start': PERIOD_START.isoformat(),
        'asof_date': ASOF_DATE.isoformat(),
        'sku': SKU,
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
    print(f"Wrote LedgerLoom Chapter 11 artifacts -> {ch_dir}")


if __name__ == "__main__":
    main()

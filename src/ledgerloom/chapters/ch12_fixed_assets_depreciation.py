"""LedgerLoom Chapter 12: Fixed assets and depreciation (deterministic generator).

This chapter introduces **fixed assets** and shows how depreciation can be
modeled as a deterministic event generator.

Key ideas
---------
- **Capitalize vs expense**: some purchases create long-lived assets; others are
  period expenses. A (tiny) policy makes this explicit.
- **Depreciation schedules**: given cost, salvage value, useful life, and a
  convention (e.g., straight-line), you can generate a predictable schedule.
- **Depreciation as events**: the schedule is converted into monthly journal
  entries (Dr Depreciation Expense, Cr Accumulated Depreciation).
- **Disposal concepts**: on sale/disposal, remove cost + accumulated
  depreciation and recognize a gain/loss versus net book value.

LedgerLoom intentionally keeps this example small and deterministic.
"""

from __future__ import annotations

import argparse
import calendar
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

CHAPTER = "ch12"
PERIOD_START = date(2026, 2, 1)
PERIOD_END = date(2026, 4, 30)
ASOF_DATE = PERIOD_END

# A simple policy knob for the teaching dataset.
CAPITALIZATION_THRESHOLD_CENTS = 250_000  # $2,500.00


@dataclass(frozen=True)
class PurchaseItem:
    item_id: str
    purchase_date: date
    description: str
    cost_cents: int


@dataclass(frozen=True)
class FixedAsset:
    asset_id: str
    description: str
    acquisition_date: date
    in_service_date: date
    cost_cents: int
    salvage_cents: int
    useful_life_months: int
    method: str = "straight_line"
    disposal_date: date | None = None
    proceeds_cents: int | None = None


def _cents(c: int) -> Decimal:
    return Decimal(cents_to_str(c))


def _tb(postings: pd.DataFrame) -> pd.DataFrame:
    return bookset.trial_balance(postings)


def _is(tb: pd.DataFrame) -> pd.DataFrame:
    return bookset.income_statement(tb)


def _bs(tb: pd.DataFrame) -> pd.DataFrame:
    return bookset.balance_sheet_adjusted(tb)


def _gl_balance_cents(tb: pd.DataFrame, account: str) -> int:
    row = tb.loc[tb["account"] == account]
    if row.empty:
        return 0
    return int(row.iloc[0]["balance"].__str__() and str_to_cents(str(row.iloc[0]["balance"])))


def _w_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    write_csv_dicts(path, rows, fieldnames=fieldnames)


def _w_df(path: Path, df: pd.DataFrame) -> None:
    write_csv_df(path, df)


def _w_json(path: Path, payload: Any) -> None:
    write_json(path, payload)


def _make_entry(entry_id: str, dt: date, narration: str, postings: list[Posting], meta: dict[str, Any]) -> Entry:
    m = {"entry_id": entry_id, "chapter": CHAPTER, **meta}
    return Entry(dt=dt, narration=narration, postings=postings, meta=m)


def _month_end(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def _iter_month_ends(start: date, months: int) -> list[date]:
    """Return month-end dates starting in ``start``'s calendar month."""

    y0, m0 = start.year, start.month
    out: list[date] = []
    for i in range(months):
        y = y0 + (m0 - 1 + i) // 12
        m = ((m0 - 1 + i) % 12) + 1
        out.append(date(y, m, calendar.monthrange(y, m)[1]))
    return out


def _purchase_dataset() -> list[PurchaseItem]:
    """Deterministic purchase stream for the chapter."""

    return [
        PurchaseItem(item_id="PO-FA-1001", purchase_date=date(2026, 2, 2), description="Laptop fleet", cost_cents=300_000),
        PurchaseItem(item_id="PO-FA-1002", purchase_date=date(2026, 2, 15), description="Forklift", cost_cents=600_000),
        PurchaseItem(item_id="PO-EXP-2001", purchase_date=date(2026, 2, 15), description="Hand tools (consumable)", cost_cents=20_000),
    ]


def _capitalization(purchases: list[PurchaseItem]) -> tuple[list[FixedAsset], list[dict[str, Any]]]:
    """Apply a tiny capitalization policy and return (assets, decision_rows)."""

    assets: list[FixedAsset] = []
    rows: list[dict[str, Any]] = []

    # Teaching profiles: in a real system these come from an asset setup screen.
    profiles = {
        "PO-FA-1001": {
            "asset_id": "FA-1001",
            "salvage_cents": 0,
            "useful_life_months": 36,
        },
        "PO-FA-1002": {
            "asset_id": "FA-1002",
            "salvage_cents": 60_000,
            "useful_life_months": 12,
            "disposal_date": date(2026, 4, 30),
            "proceeds_cents": 480_000,
        },
    }

    for p in purchases:
        decision = "capitalize" if p.cost_cents >= CAPITALIZATION_THRESHOLD_CENTS else "expense"
        rationale = (
            f"Cost >= ${cents_to_str(CAPITALIZATION_THRESHOLD_CENTS)} policy threshold"
            if decision == "capitalize"
            else "Below capitalization threshold"
        )
        rows.append(
            {
                "item_id": p.item_id,
                "purchase_date": p.purchase_date.isoformat(),
                "description": p.description,
                "cost": cents_to_str(p.cost_cents),
                "threshold": cents_to_str(CAPITALIZATION_THRESHOLD_CENTS),
                "decision": decision,
                "rationale": rationale,
            }
        )

        if decision != "capitalize":
            continue

        prof = profiles.get(p.item_id)
        if prof is None:
            raise ValueError(f"Missing asset profile for {p.item_id}")

        assets.append(
            FixedAsset(
                asset_id=str(prof["asset_id"]),
                description=p.description,
                acquisition_date=p.purchase_date,
                in_service_date=p.purchase_date,
                cost_cents=p.cost_cents,
                salvage_cents=int(prof["salvage_cents"]),
                useful_life_months=int(prof["useful_life_months"]),
                disposal_date=prof.get("disposal_date"),
                proceeds_cents=prof.get("proceeds_cents"),
            )
        )

    return assets, rows


def _depreciation_schedule(asset: FixedAsset) -> list[dict[str, Any]]:
    """Full schedule rows (may be longer than the simulated accounting period)."""

    if asset.method != "straight_line":
        raise ValueError(f"Unsupported method: {asset.method}")

    depreciable = asset.cost_cents - asset.salvage_cents
    if depreciable < 0:
        raise ValueError("salvage exceeds cost")

    monthly = depreciable // asset.useful_life_months
    remainder = depreciable - monthly * asset.useful_life_months

    ends = _iter_month_ends(asset.in_service_date, asset.useful_life_months)

    disp_end = _month_end(asset.disposal_date) if asset.disposal_date else None

    rows: list[dict[str, Any]] = []
    accum = 0
    for i, pe in enumerate(ends):
        if disp_end and pe > disp_end:
            break
        amt = monthly + (remainder if i == asset.useful_life_months - 1 else 0)
        accum += amt
        nbv = asset.cost_cents - accum
        rows.append(
            {
                "asset_id": asset.asset_id,
                "period_end": pe.isoformat(),
                "depreciation_amount": cents_to_str(amt),
                "accumulated_depreciation_end": cents_to_str(accum),
                "net_book_value_end": cents_to_str(nbv),
            }
        )
    return rows


def _accum_dep_asof(schedule_rows: list[dict[str, Any]], asof: date) -> int:
    """Accumulated depreciation (cents) through *asof* (month-end based)."""

    a = 0
    for r in schedule_rows:
        pe = date.fromisoformat(str(r["period_end"]))
        if pe <= asof:
            a = str_to_cents(str(r["accumulated_depreciation_end"]))
        else:
            break
    return a


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
    # 2) Purchases -> capitalization decisions -> asset register
    # ------------------------------------------------------------------
    purchases = _purchase_dataset()
    assets, cap_rows = _capitalization(purchases)

    # Full schedules (for explanation) + a compact event stream (for posting)
    schedule_rows: list[dict[str, Any]] = []
    schedule_by_asset: dict[str, list[dict[str, Any]]] = {}
    for a in sorted(assets, key=lambda x: x.asset_id):
        rows = _depreciation_schedule(a)
        schedule_by_asset[a.asset_id] = rows
        schedule_rows.extend(rows)

    schedule_df = pd.DataFrame(schedule_rows)
    if not schedule_df.empty:
        schedule_df = schedule_df.sort_values(["asset_id", "period_end"], kind="mergesort").reset_index(drop=True)

    register_rows: list[dict[str, Any]] = []
    for a in sorted(assets, key=lambda x: x.asset_id):
        disp = a.disposal_date.isoformat() if a.disposal_date else ""
        proceeds = cents_to_str(a.proceeds_cents) if a.proceeds_cents is not None else ""
        register_rows.append(
            {
                "asset_id": a.asset_id,
                "description": a.description,
                "acquisition_date": a.acquisition_date.isoformat(),
                "in_service_date": a.in_service_date.isoformat(),
                "cost": cents_to_str(a.cost_cents),
                "salvage_value": cents_to_str(a.salvage_cents),
                "useful_life_months": a.useful_life_months,
                "method": a.method,
                "depreciation_start": _month_end(a.in_service_date).isoformat(),
                "disposal_date": disp,
                "proceeds": proceeds,
                "status": "disposed" if a.disposal_date and a.disposal_date <= ASOF_DATE else "active",
            }
        )

    # ------------------------------------------------------------------
    # 3) Translate to G/L entries (capex + depreciation + disposal)
    # ------------------------------------------------------------------
    entries_new: list[Entry] = []

    # Expense items (below threshold)
    for p in purchases:
        if p.cost_cents >= CAPITALIZATION_THRESHOLD_CENTS:
            continue
        entries_new.append(
            _make_entry(
                entry_id=f"expense:{p.item_id}",
                dt=p.purchase_date,
                narration=f"Expense purchase {p.item_id}: {p.description}",
                postings=[
                    Posting(account="Expenses:ToolsSupplies", debit=_cents(p.cost_cents)),
                    Posting(account="Assets:Cash", credit=_cents(p.cost_cents)),
                ],
                meta={"entry_kind": "expense", "source_doc_id": p.item_id},
            )
        )

    # Capitalized acquisitions: Dr FixedAssets, Cr Cash
    for a in sorted(assets, key=lambda x: x.asset_id):
        entries_new.append(
            _make_entry(
                entry_id=f"fa_acq:{a.asset_id}",
                dt=a.acquisition_date,
                narration=f"Capitalize fixed asset {a.asset_id}: {a.description}",
                postings=[
                    Posting(account="Assets:FixedAssets:Equipment", debit=_cents(a.cost_cents)),
                    Posting(account="Assets:Cash", credit=_cents(a.cost_cents)),
                ],
                meta={"entry_kind": "acquisition", "asset_id": a.asset_id, "source_doc_id": a.asset_id},
            )
        )

    # Depreciation: one entry per asset per month-end within the simulated period.
    depr_event_rows: list[dict[str, Any]] = []
    for a in sorted(assets, key=lambda x: x.asset_id):
        rows = schedule_by_asset[a.asset_id]
        disp_end = _month_end(a.disposal_date) if a.disposal_date else None
        for r in rows:
            pe = date.fromisoformat(str(r["period_end"]))
            if pe < PERIOD_START or pe > PERIOD_END:
                continue
            if disp_end and pe > disp_end:
                continue

            amt_cents = str_to_cents(str(r["depreciation_amount"]))
            eid = f"depr:{a.asset_id}:{pe.isoformat()}"
            entries_new.append(
                _make_entry(
                    entry_id=eid,
                    dt=pe,
                    narration=f"Monthly depreciation {a.asset_id} ({pe.strftime('%Y-%m')})",
                    postings=[
                        Posting(account="Expenses:Depreciation", debit=_cents(amt_cents)),
                        Posting(account="Assets:FixedAssets:AccumulatedDepreciation", credit=_cents(amt_cents)),
                    ],
                    meta={"entry_kind": "depreciation", "asset_id": a.asset_id, "period_end": pe.isoformat()},
                )
            )
            depr_event_rows.append(
                {
                    "entry_id": eid,
                    "date": pe.isoformat(),
                    "asset_id": a.asset_id,
                    "period_end": pe.isoformat(),
                    "depreciation_amount": cents_to_str(amt_cents),
                }
            )

    # Disposal: remove cost + accumulated depreciation, record proceeds and gain/loss.
    for a in sorted(assets, key=lambda x: x.asset_id):
        if not a.disposal_date:
            continue
        if a.proceeds_cents is None:
            raise ValueError(f"Missing proceeds_cents for disposed asset {a.asset_id}")

        disp_date = a.disposal_date
        # Convention: disposal at month-end after depreciation is posted.
        accum_cents = _accum_dep_asof(schedule_by_asset[a.asset_id], _month_end(disp_date))
        nbv_cents = a.cost_cents - accum_cents
        gain_cents = a.proceeds_cents - nbv_cents

        postings: list[Posting] = [
            Posting(account="Assets:Cash", debit=_cents(a.proceeds_cents)),
            Posting(account="Assets:FixedAssets:AccumulatedDepreciation", debit=_cents(accum_cents)),
            Posting(account="Assets:FixedAssets:Equipment", credit=_cents(a.cost_cents)),
        ]
        if gain_cents >= 0:
            postings.append(Posting(account="Revenue:GainOnDisposal", credit=_cents(gain_cents)))
        else:
            postings.append(Posting(account="Expenses:LossOnDisposal", debit=_cents(-gain_cents)))

        entries_new.append(
            _make_entry(
                entry_id=f"fa_disp:{a.asset_id}",
                dt=disp_date,
                narration=f"Dispose fixed asset {a.asset_id}: {a.description}",
                postings=postings,
                meta={
                    "entry_kind": "disposal",
                    "asset_id": a.asset_id,
                    "proceeds": cents_to_str(a.proceeds_cents),
                    "net_book_value": cents_to_str(nbv_cents),
                    "gain_loss": cents_to_str(gain_cents),
                },
            )
        )

    # Build posting tables
    entries_all = [opening_entry, *entries_new]
    postings_all = engine.postings_fact_table(entries_all)

    new_entry_ids = {str(e.meta["entry_id"]) for e in entries_new}
    postings_fa = postings_all.loc[postings_all["entry_id"].isin(sorted(new_entry_ids))].copy()

    tb_end = _tb(postings_all)
    is_current = _is(tb_end)
    bs_current = _bs(tb_end)

    # Control reconciliation (net fixed assets per subledger vs G/L)
    gl_gross = _gl_balance_cents(tb_end, "Assets:FixedAssets:Equipment")
    gl_accum = _gl_balance_cents(tb_end, "Assets:FixedAssets:AccumulatedDepreciation")
    gl_net = gl_gross + gl_accum

    sub_gross = 0
    sub_accum = 0
    for a in assets:
        if a.disposal_date and a.disposal_date <= ASOF_DATE:
            continue
        sub_gross += a.cost_cents
        sub_accum += _accum_dep_asof(schedule_by_asset[a.asset_id], ASOF_DATE)
    sub_net = sub_gross - sub_accum

    recon_control = pd.DataFrame(
        [
            {
                "asof": ASOF_DATE.isoformat(),
                "gl_fixed_assets_gross": cents_to_str(gl_gross),
                "gl_accum_depreciation": cents_to_str(gl_accum),
                "gl_net_fixed_assets": cents_to_str(gl_net),
                "subledger_net_fixed_assets": cents_to_str(sub_net),
                "diff": cents_to_str(gl_net - sub_net),
            }
        ]
    )

    # Engine invariants + custom checks
    inv = engine.invariants(entries_all, postings_all)
    inv["checks"] = {
        "fixed_assets_control_reconciles": {
            "ok": gl_net == sub_net,
            "gl_net_fixed_assets": cents_to_str(gl_net),
            "subledger_net_fixed_assets": cents_to_str(sub_net),
        },
        "depreciation_events_match_schedule": {
            "ok": sum(str_to_cents(r["depreciation_amount"]) for r in depr_event_rows)
            == sum(
                str_to_cents(r["depreciation_amount"])
                for r in schedule_rows
                if PERIOD_START <= date.fromisoformat(str(r["period_end"])) <= PERIOD_END
            ),
        },
    }

    checklist = {
        "chapter": CHAPTER,
        "period_start": PERIOD_START.isoformat(),
        "period_end": PERIOD_END.isoformat(),
        "capitalization_threshold": cents_to_str(CAPITALIZATION_THRESHOLD_CENTS),
        "purchases_count": len(purchases),
        "capitalized_assets_count": len(assets),
        "depreciation_events_count": len(depr_event_rows),
        "has_disposal": any(a.disposal_date for a in assets),
        "fixed_assets_control_equals_subledger": gl_net == sub_net,
        "limitations": [
            "Straight-line depreciation only.",
            "No partial-month conventions (month-end posting for the in-service month).",
            "No componentization, revaluations, or impairment testing in the engine.",
        ],
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
        out_ch / "capitalization_decisions.csv",
        cap_rows,
        ["item_id", "purchase_date", "description", "cost", "threshold", "decision", "rationale"],
    )
    _w_csv(
        out_ch / "fixed_assets_register.csv",
        register_rows,
        [
            "asset_id",
            "description",
            "acquisition_date",
            "in_service_date",
            "cost",
            "salvage_value",
            "useful_life_months",
            "method",
            "depreciation_start",
            "disposal_date",
            "proceeds",
            "status",
        ],
    )
    _w_df(out_ch / "depreciation_schedule.csv", schedule_df)
    _w_csv(
        out_ch / "depreciation_events.csv",
        depr_event_rows,
        ["entry_id", "date", "asset_id", "period_end", "depreciation_amount"],
    )

    _w_df(out_ch / "postings_fixed_assets.csv", postings_fa)
    _w_df(out_ch / "fixed_assets_control_reconciliation.csv", recon_control)

    _w_df(out_ch / "trial_balance_end_period.csv", tb_end)
    _w_df(out_ch / "income_statement_current_period.csv", is_current)
    _w_df(out_ch / "balance_sheet_current_period.csv", bs_current)

    _w_json(out_ch / "invariants.json", inv)
    _w_json(out_ch / "fixed_assets_checklist.json", checklist)

    artifact_names = [
        "postings_post_close.csv",
        "trial_balance_post_close.csv",
        "postings_opening.csv",
        "trial_balance_opening.csv",
        "reconciliation_post_close_vs_opening.csv",
        "capitalization_decisions.csv",
        "fixed_assets_register.csv",
        "depreciation_schedule.csv",
        "depreciation_events.csv",
        "postings_fixed_assets.csv",
        "fixed_assets_control_reconciliation.csv",
        "trial_balance_end_period.csv",
        "income_statement_current_period.csv",
        "balance_sheet_current_period.csv",
        "invariants.json",
        "fixed_assets_checklist.json",
    ]
    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        'chapter': CHAPTER,
        'module': 'ledgerloom.chapters.ch12_fixed_assets_depreciation',
        'seed': seed,
        'asof_date': ASOF_DATE.isoformat(),
        'capitalization_threshold_cents': CAPITALIZATION_THRESHOLD_CENTS,
        'method': 'straight_line',
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

    ch_dir = run(outdir=args.outdir, seed=args.seed)
    print(f"Wrote LedgerLoom Chapter 12 artifacts -> {ch_dir}")


if __name__ == "__main__":
    main()

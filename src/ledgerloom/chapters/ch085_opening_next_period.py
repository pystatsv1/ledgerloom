"""LedgerLoom Chapter 08.5 — Opening the next period.

Story beat: after Ch08's close, we carry forward permanent account balances into the
next period and show retained earnings continuity. This is the bridge chapter that
connects the close cycle (Part II) to operational cycles (Part III).

Outputs are deterministic and include an explicit reconciliation against Ch08's
post-close trial balance.
"""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.engine.ledger import LedgerEngine
from ledgerloom.engine.config import LedgerEngineConfig

from ledgerloom.artifacts import manifest_items_prefixed, write_csv_df, write_json
from ledgerloom.trust.pipeline import emit_trust_artifacts
from ledgerloom.engine.money import cents_to_str, str_to_cents
from ledgerloom.scenarios.bookset_v1 import compute_post_close_snapshot

# Re-use Ch08's scenario + report helpers to guarantee continuity.
CHAPTER = "ch085"
OUTDIR_NAME = "ch085"
CLOSE_DATE = date(2026, 1, 31)
OPEN_DATE = date(2026, 2, 1)
CLOSE_PERIOD = "2026-01"


def _w_csv(df: pd.DataFrame, path: Path) -> None:
    """Backward-compatible wrapper around :func:`ledgerloom.artifacts.write_csv_df`.

    Chapter 08.5 was used to validate cross-platform newline stability.
    Keeping this wrapper makes diffs small while still centralizing I/O.
    """

    write_csv_df(path, df)


def _w_json(obj: Any, path: Path) -> None:
    """Backward-compatible wrapper around :func:`ledgerloom.artifacts.write_json`."""

    write_json(path, obj)



def _make_entry(entry_id: str, dt: date, narration: str, lines: list[tuple[str, str, str]], meta: dict[str, Any]) -> Entry:
    postings: list[Posting] = []
    for acct, dr, cr in lines:
        postings.append(Posting(account=acct, debit=Decimal(dr), credit=Decimal(cr)))
    merged = {"entry_id": entry_id, **(meta or {})}
    return Entry(dt=dt, narration=narration, postings=postings, meta=merged)


def _trial_balance_from_postings(postings: pd.DataFrame) -> pd.DataFrame:
    """Trial balance in normal-sign convention (uses postings.signed_delta)."""
    g = (
        postings.groupby(["account", "root"], sort=True)["signed_delta"]
        .apply(lambda s: sum(str_to_cents(x) for x in s))
        .reset_index(name="balance_cents")
    )
    g["balance"] = g["balance_cents"].apply(cents_to_str)
    return g[["account", "root", "balance"]].sort_values(["root", "account"], ignore_index=True)


def _compute_ch08_post_close(cfg: LedgerEngineConfig) -> dict[str, Any]:
    """Compute Ch08 post-close artifacts in-memory (no filesystem dependency).

    This chapter previously reached into Chapter 08 private helpers. We now treat
    the scenario layer as the shared, public API for "close → post-close snapshot".
    """

    snap = compute_post_close_snapshot(cfg=cfg, period=CLOSE_PERIOD, close_date=CLOSE_DATE)

    return {
        "adjusted_entries": snap.adjusted_entries,
        "closing_entries": snap.closing_entries,
        "post_close_entries": snap.post_close_entries,
        "postings_adjusted": snap.postings_adjusted,
        "postings_post_close": snap.postings_post_close,
        "tb_adjusted": snap.trial_balance_adjusted,
        "tb_post_close": snap.trial_balance_post_close,
        "bs_post_close": snap.balance_sheet_post_close,
        "engine": LedgerEngine(cfg),
    }
def _opening_entry_from_post_close_tb(tb_post_close: pd.DataFrame, cfg: LedgerEngineConfig) -> Entry:
    """Build an opening balance entry from the post-close trial balance.

    We only carry forward permanent accounts (Assets/Liabilities/Equity). Revenue/Expenses
    are expected to start the new period at 0.00 (and will be represented as such in the
    opening trial balance output).
    """
    rows = tb_post_close.copy()
    rows["balance_cents"] = rows["balance"].apply(str_to_cents)
    rows = rows[rows["root"].isin({"Assets", "Liabilities", "Equity"})].copy()
    rows = rows[rows["balance_cents"] != 0].copy()

    root_order = {"Assets": 0, "Liabilities": 1, "Equity": 2}
    rows["_root_order"] = rows["root"].map(root_order).astype(int)
    rows = rows.sort_values(["_root_order", "account"], ignore_index=True)

    lines: list[tuple[str, str, str]] = []
    total_debits = 0
    total_credits = 0

    for _, r in rows.iterrows():
        account = str(r["account"])
        root = str(r["root"])
        bal = int(r["balance_cents"])

        if root in cfg.debit_normal_roots:
            # debit-normal: signed = debit - credit
            if bal >= 0:
                debit_cents, credit_cents = bal, 0
            else:
                debit_cents, credit_cents = 0, -bal
        elif root in cfg.credit_normal_roots:
            # credit-normal: signed = credit - debit
            if bal >= 0:
                debit_cents, credit_cents = 0, bal
            else:
                debit_cents, credit_cents = -bal, 0
        else:
            raise ValueError(f"Unknown root for opening balance logic: {root}")

        total_debits += debit_cents
        total_credits += credit_cents

        lines.append(
            (
                account,
                cents_to_str(debit_cents),
                cents_to_str(credit_cents),
            )
        )

    if total_debits != total_credits:
        raise ValueError(
            "Opening entry not balanced "
            f"(debits={cents_to_str(total_debits)}, credits={cents_to_str(total_credits)})"
        )

    return _make_entry(
        "OPEN-2026-02-01",
        OPEN_DATE,
        "Opening balance carry-forward (from Ch08 post-close)",
        lines,
        meta={"chapter": CHAPTER, "department": "HQ", "source": "ch08_post_close"},
    )


def _tb_full_template(tb_template: pd.DataFrame, tb_partial: pd.DataFrame) -> pd.DataFrame:
    """Fill a TB with the template account list, inserting explicit 0.00 rows."""
    bal_map = dict(zip(tb_partial["account"], tb_partial["balance"]))
    out = tb_template[["account", "root"]].copy()
    out["balance"] = [bal_map.get(a, "0.00") for a in out["account"]]
    return out


def _balance_sheet_from_tb(tb: pd.DataFrame) -> pd.DataFrame:
    rows = tb[tb["root"].isin({"Assets", "Liabilities", "Equity"})].copy()
    rows["balance_cents"] = rows["balance"].apply(str_to_cents)
    g = rows.groupby("root", sort=False)["balance_cents"].sum().reset_index()
    g["amount"] = g["balance_cents"].apply(cents_to_str)
    return g[["root", "amount"]]


def _continuity_tables(tb_post_close: pd.DataFrame, tb_opening: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (reconciliation_by_account, retained_earnings_continuity)."""
    post = tb_post_close.copy().rename(columns={"balance": "post_close_balance"})
    open_ = tb_opening.copy().rename(columns={"balance": "opening_balance"})
    merged = post.merge(open_[["account", "opening_balance"]], on="account", how="left")
    merged["opening_balance"] = merged["opening_balance"].fillna("0.00")

    merged["diff_cents"] = merged.apply(
        lambda r: str_to_cents(r["opening_balance"]) - str_to_cents(r["post_close_balance"]),
        axis=1,
    )
    merged["diff"] = merged["diff_cents"].apply(cents_to_str)
    merged = merged[["account", "root", "post_close_balance", "opening_balance", "diff"]]

    def _get_balance(tb_df: pd.DataFrame, account: str) -> str:
        col = "balance"
        if col not in tb_df.columns:
            return "0.00"
        m = tb_df.loc[tb_df["account"] == account, col]
        if len(m) == 0:
            return "0.00"
        return str(m.iloc[0])

    re_account = "Equity:RetainedEarnings"
    re_post = _get_balance(tb_post_close, re_account)
    re_open = _get_balance(tb_opening, re_account)

    re_df = pd.DataFrame(
        [
            {"stage": "post_close (Ch08)", "account": re_account, "amount": re_post},
            {"stage": "opening (Ch08.5)", "account": re_account, "amount": re_open},
            {
                "stage": "diff",
                "account": re_account,
                "amount": cents_to_str(str_to_cents(re_open) - str_to_cents(re_post)),
            },
        ]
    )

    return merged, re_df


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("outputs/ledgerloom"))
    parser.add_argument("--seed", type=int, default=123, help="Reserved for future deterministic variants.")
    args = parser.parse_args(argv)

    outdir = args.outdir / OUTDIR_NAME
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = LedgerEngineConfig()

    # --- Source-of-truth: compute Ch08 post-close in-memory ---
    src = _compute_ch08_post_close(cfg)
    tb_post_close: pd.DataFrame = src["tb_post_close"]
    bs_post_close: pd.DataFrame = src["bs_post_close"]

    # --- New period: opening entry built from post-close TB ---
    opening_entry = _opening_entry_from_post_close_tb(tb_post_close, cfg)
    opening_entries = [opening_entry]

    engine_open = LedgerEngine(cfg)
    postings_opening = engine_open.postings_fact_table(opening_entries)
    tb_opening_partial = _trial_balance_from_postings(postings_opening)
    tb_opening = _tb_full_template(tb_post_close, tb_opening_partial)

    bs_opening = _balance_sheet_from_tb(tb_opening)

    recon_by_account, re_continuity = _continuity_tables(tb_post_close, tb_opening)

    # Register: one entry summary
    total_debits = sum(str_to_cents(x) for x in postings_opening["debit"])
    total_credits = sum(str_to_cents(x) for x in postings_opening["credit"])
    entry_register = pd.DataFrame(
        [
            {
                "entry_id": str(opening_entry.meta.get("entry_id", "")),
                "entry_date": opening_entry.dt.isoformat(),
                "narration": opening_entry.narration,
                "post_close_date": CLOSE_DATE.isoformat(),
                "open_date": OPEN_DATE.isoformat(),
                "lines": len(opening_entry.postings),
                "total_debits": cents_to_str(total_debits),
                "total_credits": cents_to_str(total_credits),
            }
        ]
    )

    # --- Write artifacts ---
    _w_csv(tb_post_close, outdir / "trial_balance_post_close.csv")
    _w_csv(bs_post_close, outdir / "balance_sheet_post_close.csv")

    _w_csv(entry_register, outdir / "opening_entry_register.csv")
    _w_csv(postings_opening, outdir / "postings_opening.csv")
    _w_csv(tb_opening, outdir / "trial_balance_opening.csv")
    _w_csv(bs_opening, outdir / "balance_sheet_opening.csv")
    _w_csv(recon_by_account, outdir / "reconciliation_post_close_vs_opening.csv")
    _w_csv(re_continuity, outdir / "retained_earnings_continuity.csv")

    checklist = {
        "chapter": CHAPTER,
        "close_date": CLOSE_DATE.isoformat(),
        "open_date": OPEN_DATE.isoformat(),
        "expectations": [
            "Post-close TB (Ch08) is the source-of-truth for carry-forward balances.",
            "Opening TB (Ch08.5) matches Ch08 post-close for all permanent accounts.",
            "Revenue/Expenses open at 0.00 for the new period.",
            "Retained earnings continuity holds.",
        ],
    }
    _w_json(checklist, outdir / "opening_checklist.json")

    inv_open = engine_open.invariants(opening_entries, postings_opening)

    diffs = recon_by_account["diff"].apply(str_to_cents)
    continuity = {
        "checks": [
            {
                "name": "post_close_vs_opening_all_accounts_match",
                "ok": bool((diffs == 0).all()),
                "max_abs_diff": cents_to_str(int(diffs.abs().max() if len(diffs) else 0)),
            },
            {
                "name": "opening_entry_balanced",
                "ok": bool(total_debits == total_credits),
                "debits": cents_to_str(total_debits),
                "credits": cents_to_str(total_credits),
            },
            {
                "name": "retained_earnings_continuity",
                "ok": bool(str_to_cents(re_continuity.iloc[2]["amount"]) == 0),
                "post_close": str(re_continuity.iloc[0]["amount"]),
                "opening": str(re_continuity.iloc[1]["amount"]),
                "diff": str(re_continuity.iloc[2]["amount"]),
            },
        ]
    }

    invariants_obj = {
        "chapter": CHAPTER,
        "engine_opening": inv_open,
        "continuity": continuity,
    }
    _w_json(invariants_obj, outdir / "invariants.json")

    artifact_names = [
        "trial_balance_post_close.csv",
        "balance_sheet_post_close.csv",
        "opening_entry_register.csv",
        "postings_opening.csv",
        "trial_balance_opening.csv",
        "balance_sheet_opening.csv",
        "reconciliation_post_close_vs_opening.csv",
        "retained_earnings_continuity.csv",
        "opening_checklist.json",
        "invariants.json",
    ]

    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        "chapter": CHAPTER,
        "module": "ledgerloom.chapters.ch085_opening_next_period",
        "seed": args.seed,
        "close_date": CLOSE_DATE.isoformat(),
        "open_date": OPEN_DATE.isoformat(),
        "source": "ch08_post_close",
    }

    def _manifest_payload(d: Path) -> dict[str, object]:
        names = list(artifact_names) + ["run_meta.json"]
        return {
            "meta": {
                "chapter": CHAPTER,
                "seed": args.seed,
                "close_date": CLOSE_DATE.isoformat(),
                "open_date": OPEN_DATE.isoformat(),
                "source": "ch08_post_close",
            },
            "artifacts": manifest_items_prefixed(d, names, prefix=OUTDIR_NAME, name_key="path"),
        }

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=_manifest_payload)

    print(f"Wrote LedgerLoom Chapter 08.5 artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
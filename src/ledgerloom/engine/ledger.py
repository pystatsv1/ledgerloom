"""Ledger engine (v0.1).

The engine takes a list of :class:`ledgerloom.core.Entry` objects and produces
canonical ledger tables:

- postings: one row per posting line (fact table)
- balance views: by account / period / segment
- invariants: explicit constraints you can assert in tests

This module intentionally stays "boring": it copies chapter logic into a reusable
core, keeping byte-for-byte identical artifacts when chapters call it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pandas as pd

from ledgerloom.core import Entry

from .config import LedgerEngineConfig
from .money import cents_to_str, to_cents


def account_root(account: str) -> str:
    """Return the root segment of a colon-path account."""

    return account.split(":", 1)[0]


def entry_id(entry: Entry, cfg: LedgerEngineConfig) -> str:
    """Stable identifier for an entry (stored in ``entry.meta``)."""

    v = (entry.meta or {}).get(cfg.entry_id_key)
    return str(v) if v is not None else ""


def entry_department(entry: Entry, cfg: LedgerEngineConfig) -> str:
    """Simple segment value used for grouping (stored in ``entry.meta``)."""

    v = (entry.meta or {}).get(cfg.department_key)
    return str(v) if v is not None else ""


def signed_cents(cfg: LedgerEngineConfig, root: str, debit_cents: int, credit_cents: int) -> int:
    """Return balance delta in the account's *normal* sign convention."""

    if root in cfg.debit_normal_roots:
        return debit_cents - credit_cents
    if root in cfg.credit_normal_roots:
        return credit_cents - debit_cents
    # Unknown root: treat like debit-normal, but invariants should flag this.
    return debit_cents - credit_cents


def postings_fact_table(entries: list[Entry], cfg: LedgerEngineConfig) -> pd.DataFrame:
    """Build the postings fact table (one row per posting line)."""

    rows: list[dict[str, Any]] = []
    for e in entries:
        dept = entry_department(e, cfg)
        for i, p in enumerate(e.postings, start=1):
            root = account_root(p.account)
            dr_c = to_cents(p.debit)
            cr_c = to_cents(p.credit)
            rows.append(
                {
                    "posting_id": f"{entry_id(e, cfg)}:{i:02d}",
                    "entry_id": entry_id(e, cfg),
                    "line_no": i,
                    "date": e.dt.isoformat(),
                    "department": dept,
                    "narration": e.narration,
                    "account": p.account,
                    "root": root,
                    "debit": cents_to_str(dr_c),
                    "credit": cents_to_str(cr_c),
                    "raw_delta": cents_to_str(dr_c - cr_c),
                    "signed_delta": cents_to_str(signed_cents(cfg, root, dr_c, cr_c)),
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["date", "entry_id", "line_no"], kind="mergesort").reset_index(drop=True)
    return df


def balances_by_account(postings: pd.DataFrame, cfg: LedgerEngineConfig) -> pd.DataFrame:
    """Materialized view: balances grouped by account."""

    tmp = postings.copy()
    for col in ["debit", "credit", "raw_delta", "signed_delta"]:
        tmp[f"{col}_cents"] = tmp[col].map(lambda s: int(Decimal(s) * 100))

    g = tmp.groupby(["root", "account"], sort=True, as_index=False).agg(
        debit_cents=("debit_cents", "sum"),
        credit_cents=("credit_cents", "sum"),
        signed_cents=("signed_delta_cents", "sum"),
    )

    def normal_side(root: str) -> str:
        if root in cfg.debit_normal_roots:
            return "debit"
        if root in cfg.credit_normal_roots:
            return "credit"
        return "unknown"

    g["normal_side"] = g["root"].map(normal_side)
    g["debit_total"] = g["debit_cents"].map(cents_to_str)
    g["credit_total"] = g["credit_cents"].map(cents_to_str)
    g["balance"] = g["signed_cents"].map(cents_to_str)

    out = g[["root", "account", "normal_side", "debit_total", "credit_total", "balance"]]
    out = out.sort_values(["root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def balances_by_period(postings: pd.DataFrame) -> pd.DataFrame:
    """Materialized view: balances grouped by period (YYYY-MM) and account."""

    tmp = postings.copy()
    tmp["period"] = tmp["date"].str.slice(0, 7)  # YYYY-MM
    tmp["signed_cents"] = tmp["signed_delta"].map(lambda s: int(Decimal(s) * 100))

    g = tmp.groupby(["period", "root", "account"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(cents_to_str)
    out = g[["period", "root", "account", "balance"]]
    out = out.sort_values(["period", "root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def balances_by_department(postings: pd.DataFrame) -> pd.DataFrame:
    """Materialized view: balances grouped by department and root."""

    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(lambda s: int(Decimal(s) * 100))

    g = tmp.groupby(["department", "root"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(cents_to_str)
    out = g[["department", "root", "balance"]]
    out = out.sort_values(["department", "root"], kind="mergesort").reset_index(drop=True)
    return out


def running_balance_by_posting(postings: pd.DataFrame) -> pd.DataFrame:
    """Window-function style running balances per account."""

    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(lambda s: int(Decimal(s) * 100))

    tmp = tmp.sort_values(["account", "date", "entry_id", "line_no"], kind="mergesort").reset_index(drop=True)
    tmp["running_balance_cents"] = tmp.groupby("account", sort=True)["signed_cents"].cumsum()
    tmp["running_balance"] = tmp["running_balance_cents"].map(cents_to_str)

    out = tmp[
        [
            "posting_id",
            "date",
            "account",
            "signed_delta",
            "running_balance",
            "department",
            "narration",
        ]
    ]
    out = out.sort_values(["account", "date", "posting_id"], kind="mergesort").reset_index(drop=True)
    return out


def invariants(entries: list[Entry], postings: pd.DataFrame, cfg: LedgerEngineConfig) -> dict[str, Any]:
    """Compute core invariants for a balanced ledger."""

    entry_rows = []
    for e in entries:
        dr = sum((to_cents(p.debit) for p in e.postings), 0)
        cr = sum((to_cents(p.credit) for p in e.postings), 0)
        entry_rows.append({"entry_id": entry_id(e, cfg), "debits": dr, "credits": cr, "ok": dr == cr})

    entry_ok = all(r["ok"] for r in entry_rows)

    raw_total_cents = int(sum(Decimal(x) for x in postings["raw_delta"]) * 100)

    roots = sorted(set(postings["root"].tolist()))
    recognized_roots = sorted(cfg.recognized_roots)
    unknown_roots = sorted(set(roots) - set(recognized_roots))

    posting_id_unique = postings["posting_id"].is_unique

    return {
        "entry_double_entry_ok": entry_ok,
        "entry_double_entry_failures": [r for r in entry_rows if not r["ok"]],
        "ledger_raw_delta_zero": raw_total_cents == 0,
        "ledger_raw_delta_total": cents_to_str(raw_total_cents),
        "posting_id_unique": posting_id_unique,
        "roots_seen": roots,
        "unknown_roots": unknown_roots,
        "notes": [
            "Raw delta uses (debit-credit). It must sum to 0 for a balanced ledger.",
            "Signed delta uses a normal-balance convention by root (Assets/Expenses debit-normal; Liabilities/Equity/Revenue credit-normal).",
        ],
    }


def gl_schema_description() -> dict[str, Any]:
    """A tiny schema description for the GL tables (for docs/tooling)."""

    return {
        "tables": {
            "postings": {
                "description": "Fact table: one row per posting line (debit or credit).",
                "primary_key": ["posting_id"],
                "columns": [
                    {"name": "posting_id", "type": "string", "example": "E0001:01"},
                    {"name": "entry_id", "type": "string"},
                    {"name": "line_no", "type": "int"},
                    {"name": "date", "type": "date (YYYY-MM-DD)"},
                    {"name": "department", "type": "string"},
                    {"name": "narration", "type": "string"},
                    {"name": "account", "type": "string"},
                    {"name": "root", "type": "string"},
                    {"name": "debit", "type": "decimal (string)"},
                    {"name": "credit", "type": "decimal (string)"},
                    {"name": "raw_delta", "type": "decimal (string)", "meaning": "debit - credit"},
                    {
                        "name": "signed_delta",
                        "type": "decimal (string)",
                        "meaning": "delta in the account's normal-balance convention",
                    },
                ],
                "index_suggestions": [
                    ["date"],
                    ["account", "date"],
                    ["department", "date"],
                ],
            },
            "balances_by_account": {
                "description": "Materialized view: balances grouped by account.",
                "primary_key": ["account"],
            },
            "balances_by_period": {
                "description": "Materialized view: balances grouped by period (YYYY-MM) and account.",
                "primary_key": ["period", "account"],
            },
            "balances_by_department": {
                "description": "Materialized view: balances grouped by department and root.",
                "primary_key": ["department", "root"],
            },
        }
    }


@dataclass(frozen=True)
class LedgerEngine:
    """The reusable ledger compute engine.

    v0.1 minimal API surface (methods):
    - postings_fact_table
    - balances_by_account
    - balances_by_period
    - balances_by_department
    - running_balance_by_posting
    - invariants
    - gl_schema_description
    """

    cfg: LedgerEngineConfig = field(default_factory=LedgerEngineConfig)

    def postings_fact_table(self, entries: list[Entry]) -> pd.DataFrame:
        return postings_fact_table(entries, cfg=self.cfg)

    def balances_by_account(self, postings: pd.DataFrame) -> pd.DataFrame:
        return balances_by_account(postings, cfg=self.cfg)

    def balances_by_period(self, postings: pd.DataFrame) -> pd.DataFrame:
        return balances_by_period(postings)

    def balances_by_department(self, postings: pd.DataFrame) -> pd.DataFrame:
        return balances_by_department(postings)

    def running_balance_by_posting(self, postings: pd.DataFrame) -> pd.DataFrame:
        return running_balance_by_posting(postings)

    def invariants(self, entries: list[Entry], postings: pd.DataFrame) -> dict[str, Any]:
        return invariants(entries, postings, cfg=self.cfg)

    def gl_schema_description(self) -> dict[str, Any]:
        return gl_schema_description()

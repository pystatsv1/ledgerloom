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
from datetime import date
from typing import Any

import hashlib

import pandas as pd

from ledgerloom.core import Entry

from .config import LedgerEngineConfig
from .money import cents_to_str, str_to_cents, to_cents


def account_root(account: str) -> str:
    """Return the root segment of a colon-path account."""

    return account.split(":", 1)[0]


def entry_id(entry: Entry, cfg: LedgerEngineConfig) -> str:
    """Return the stable identifier for an entry.

    By default, LedgerLoom treats ``entry.meta[cfg.entry_id_key]`` as required.
    This is a pragmatic constraint for real systems: it makes matching,
    reconciliation, and traceability explicit.

    The behavior is controlled by :attr:`ledgerloom.engine.config.LedgerEngineConfig.entry_id_policy`:

    - ``"strict"``: raise if missing
    - ``"generated"``: synthesize a deterministic id from entry content
    """

    v = (entry.meta or {}).get(cfg.entry_id_key)
    if v is not None and str(v) != "":
        return str(v)

    if cfg.entry_id_policy == "generated":
        return _generated_entry_id(entry)

    raise ValueError(
        f"Entry is missing required meta['{cfg.entry_id_key}'] (entry_id_policy='strict'). "
        "Set entry_id on every Entry, or use LedgerEngineConfig(entry_id_policy='generated')."
    )


def _generated_entry_id(entry: Entry) -> str:
    """Synthesize a deterministic entry_id from entry content.

    This is intended for teaching, migration, and exploratory notebooks.
    Production systems should prefer explicit IDs so humans can join ledger
    rows back to source documents.
    """

    h = hashlib.sha256()
    h.update(entry.dt.isoformat().encode("utf-8"))
    h.update(b"\x1f")
    h.update(entry.narration.encode("utf-8"))
    h.update(b"\x1f")
    # postings are already validated by chapters/tests; still, stabilize order.
    for p in entry.postings:
        h.update(p.account.encode("utf-8"))
        h.update(b"\x1e")
        h.update(str(p.debit).encode("utf-8"))
        h.update(b"\x1d")
        h.update(str(p.credit).encode("utf-8"))
        h.update(b"\x1f")
    return "H" + h.hexdigest()[:12]


def entry_dimensions(entry: Entry, cfg: LedgerEngineConfig) -> dict[str, str]:
    """Return configured dimension values for this entry.

    Dimensions are read from ``Entry.meta`` and materialized as columns on the
    postings fact table. Missing keys fall back to each dimension's ``default``.
    """

    out: dict[str, str] = {}
    meta = entry.meta or {}
    for dim in cfg.effective_dimensions:
        v = meta.get(dim.key, dim.default)
        out[dim.name] = str(v) if v is not None else dim.default
    return out


def entry_department(entry: Entry, cfg: LedgerEngineConfig) -> str:
    """Backward-compatible helper: the configured "department" dimension value."""

    dims = entry_dimensions(entry, cfg)
    return dims.get("department", "")


def signed_cents(cfg: LedgerEngineConfig, root: str, debit_cents: int, credit_cents: int) -> int:
    """Return balance delta in the account's *normal* sign convention."""

    if root in cfg.debit_normal_roots:
        return debit_cents - credit_cents
    if root in cfg.credit_normal_roots:
        return credit_cents - debit_cents
    # Unknown root: treat like debit-normal, but invariants should flag this.
    return debit_cents - credit_cents



def validate_entries(entries: list[Entry], cfg: LedgerEngineConfig) -> None:
    """Optional strict validation for real-world usage (opt-in).

    This function is intentionally separate from invariants:
    - invariants are *reports* you can assert in tests
    - strict validation is an *exception-throwing gate* you can enable in apps

    Enabled by setting ``LedgerEngineConfig.strict_validation = True`` or by
    calling :meth:`ledgerloom.engine.ledger.LedgerEngine.validate_entries`.
    """

    errors: list[str] = []

    for ei, e in enumerate(entries):
        # Balanced entry check (double-entry invariant).
        try:
            e.validate_balanced()
        except Exception as ex:  # noqa: BLE001
            errors.append(f"entry[{ei}] {ex}")

        # Strict entry_id presence if configured.
        if cfg.entry_id_policy == "strict":
            v = (e.meta or {}).get(cfg.entry_id_key)
            if v is None or str(v).strip() == "":
                errors.append(f"entry[{ei}] missing required meta['{cfg.entry_id_key}']")

        # Required dimensions (read from Entry.meta).
        meta = e.meta or {}
        for dim in cfg.effective_dimensions:
            if not dim.required:
                continue
            v = meta.get(dim.key)
            if v is None or str(v).strip() == "":
                errors.append(f"entry[{ei}] missing required dimension '{dim.name}' (meta['{dim.key}'])")

        # Posting line rules.
        for li, p in enumerate(e.postings, start=1):
            if p.debit < 0 or p.credit < 0:
                errors.append(f"entry[{ei}] posting line {li}: debit/credit must be non-negative")
            if (p.debit > 0) == (p.credit > 0):
                errors.append(f"entry[{ei}] posting line {li}: must have exactly one of debit or credit > 0")

    if errors:
        msg = "LedgerEngine strict validation failed:\n- " + "\n- ".join(errors)
        raise ValueError(msg)


def postings_fact_table(entries: list[Entry], cfg: LedgerEngineConfig) -> pd.DataFrame:
    """Build the postings fact table (one row per posting line)."""

    if cfg.strict_validation:
        validate_entries(entries, cfg)

    rows: list[dict[str, Any]] = []
    for e in entries:
        dims = entry_dimensions(e, cfg)
        eid = entry_id(e, cfg)
        for i, p in enumerate(e.postings, start=1):
            root = account_root(p.account)
            dr_c = to_cents(p.debit)
            cr_c = to_cents(p.credit)

            # Keep column order stable (important for golden artifacts).
            row: dict[str, Any] = {
                "posting_id": f"{eid}:{i:02d}",
                "entry_id": eid,
                "line_no": i,
                "date": e.dt.isoformat(),
            }
            row.update(dims)
            row.update(
                {
                    "narration": e.narration,
                    "account": p.account,
                    "root": root,
                    "debit": cents_to_str(dr_c),
                    "credit": cents_to_str(cr_c),
                    "raw_delta": cents_to_str(dr_c - cr_c),
                    "signed_delta": cents_to_str(signed_cents(cfg, root, dr_c, cr_c)),
                }
            )
            rows.append(row)

    # If there are no entries, ``rows`` is empty and pandas would create an
    # empty DataFrame with *no columns*. Downstream code (and determinism
    # guarantees) expect the postings schema to exist even when empty.
    dim_cols = [d.name for d in cfg.effective_dimensions]
    cols = (
        ["posting_id", "entry_id", "line_no", "date"]
        + dim_cols
        + [
            "narration",
            "account",
            "root",
            "debit",
            "credit",
            "raw_delta",
            "signed_delta",
        ]
    )

    df = pd.DataFrame(rows, columns=cols)
    df = df.sort_values(["date", "entry_id", "line_no"], kind="mergesort").reset_index(drop=True)
    return df


def postings_as_of(postings: pd.DataFrame, as_of: date | str) -> pd.DataFrame:
    """Filter postings to rows with ``date <= as_of``.

    The postings table stores dates as ISO strings (YYYY-MM-DD), so lexical
    comparison is safe and deterministic.
    """

    if isinstance(as_of, date):
        as_of_s = as_of.isoformat()
    else:
        as_of_s = str(as_of)

    out = postings.loc[postings["date"] <= as_of_s].copy()
    return out.reset_index(drop=True)



def balances_by_account(postings: pd.DataFrame, cfg: LedgerEngineConfig) -> pd.DataFrame:
    """Materialized view: balances grouped by account."""

    tmp = postings.copy()
    for col in ["debit", "credit", "raw_delta", "signed_delta"]:
        tmp[f"{col}_cents"] = tmp[col].map(str_to_cents)

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
    tmp["signed_cents"] = tmp["signed_delta"].map(str_to_cents)

    g = tmp.groupby(["period", "root", "account"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(cents_to_str)
    out = g[["period", "root", "account", "balance"]]
    out = out.sort_values(["period", "root", "account"], kind="mergesort").reset_index(drop=True)
    return out


def balances_by_dimension(postings: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Materialized view: balances grouped by a dimension and root."""

    if dimension not in postings.columns:
        raise KeyError(f"postings table does not have dimension column: {dimension!r}")

    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(str_to_cents)

    g = tmp.groupby([dimension, "root"], sort=True, as_index=False).agg(
        signed_cents=("signed_cents", "sum"),
    )
    g["balance"] = g["signed_cents"].map(cents_to_str)

    out = g[[dimension, "root", "balance"]]
    out = out.sort_values([dimension, "root"], kind="mergesort").reset_index(drop=True)
    return out


def balances_by_department(postings: pd.DataFrame) -> pd.DataFrame:
    """Materialized view: balances grouped by department and root."""

    return balances_by_dimension(postings, dimension="department")


def running_balance_by_posting(postings: pd.DataFrame, cfg: LedgerEngineConfig | None = None) -> pd.DataFrame:
    """Window-function style running balances per account."""

    if cfg is None:
        dim_cols = ["department"] if "department" in postings.columns else []
    else:
        dim_cols = [d.name for d in cfg.effective_dimensions if d.name in postings.columns]

    tmp = postings.copy()
    tmp["signed_cents"] = tmp["signed_delta"].map(str_to_cents)

    tmp = tmp.sort_values(["account", "date", "entry_id", "line_no"], kind="mergesort").reset_index(drop=True)
    tmp["running_balance_cents"] = tmp.groupby("account", sort=True)["signed_cents"].cumsum()
    tmp["running_balance"] = tmp["running_balance_cents"].map(cents_to_str)

    out_cols = [
        "posting_id",
        "date",
        "account",
        "signed_delta",
        "running_balance",
        *dim_cols,
        "narration",
    ]
    out = tmp[out_cols]
    out = out.reset_index(drop=True)
    return out


def invariants(entries: list[Entry], postings: pd.DataFrame, cfg: LedgerEngineConfig) -> dict[str, Any]:
    """Compute core invariants for a balanced ledger."""

    entry_rows = []
    generated_entry_ids: list[dict[str, Any]] = []

    for e in entries:
        dr = sum((to_cents(p.debit) for p in e.postings), 0)
        cr = sum((to_cents(p.credit) for p in e.postings), 0)

        raw_v = (e.meta or {}).get(cfg.entry_id_key)
        has_explicit_id = raw_v is not None and str(raw_v) != ""
        eid = entry_id(e, cfg)

        if cfg.entry_id_policy == "generated" and not has_explicit_id:
            generated_entry_ids.append(
                {
                    "entry_id": eid,
                    "date": e.dt.isoformat(),
                    "narration": e.narration,
                    "reason": f"missing meta['{cfg.entry_id_key}']",
                }
            )

        entry_rows.append({"entry_id": eid, "debits": dr, "credits": cr, "ok": dr == cr})

    entry_ok = all(r["ok"] for r in entry_rows)

    raw_total_cents = int(postings["raw_delta"].map(str_to_cents).sum())

    roots = sorted(set(postings["root"].tolist()))
    recognized_roots = sorted(cfg.recognized_roots)
    unknown_roots = sorted(set(roots) - set(recognized_roots))

    posting_id_unique = bool(postings["posting_id"].is_unique)

    # Contract-level checks (useful for teaching and safe refactors).
    entry_ids = [r["entry_id"] for r in entry_rows]
    missing_entry_ids = [r for r in entry_rows if not r["entry_id"]]
    entry_id_present = len(missing_entry_ids) == 0
    entry_id_unique = len(set(entry_ids)) == len(entry_ids)

    pid_series = postings["posting_id"].astype(str)
    posting_id_format_ok = bool(pid_series.str.match(r".+:\d{2}$").all()) if len(postings) else True
    date_format_ok = bool(postings["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$").all()) if len(postings) else True

    def _pid_prefix_ok(r: pd.Series) -> bool:
        return str(r["posting_id"]).startswith(f"{r['entry_id']}:")

    def _pid_suffix_ok(r: pd.Series) -> bool:
        return str(r["posting_id"]).endswith(f":{int(r['line_no']):02d}")

    posting_id_entry_id_ok = bool(postings.apply(_pid_prefix_ok, axis=1).all()) if len(postings) else True
    posting_id_line_no_ok = bool(postings.apply(_pid_suffix_ok, axis=1).all()) if len(postings) else True

    bad_posting_ids = []
    if len(postings):
        mask = ~(pid_series.str.match(r".+:\d{2}$") & postings.apply(_pid_prefix_ok, axis=1) & postings.apply(_pid_suffix_ok, axis=1))
        if mask.any():
            bad_posting_ids = postings.loc[mask, ["posting_id", "entry_id", "line_no", "date"]].head(25).to_dict("records")

    bad_dates = []
    if len(postings) and not date_format_ok:
        bad_dates = postings.loc[~postings["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$"), ["posting_id", "date"]].head(25).to_dict("records")

    return {
        "entry_double_entry_ok": entry_ok,
        "entry_double_entry_failures": [r for r in entry_rows if not r["ok"]],
        "ledger_raw_delta_zero": raw_total_cents == 0,
        "ledger_raw_delta_total": cents_to_str(raw_total_cents),
        "posting_id_unique": posting_id_unique,
        "entry_id_present": entry_id_present,
        "entry_id_unique": entry_id_unique,
        "missing_entry_ids": missing_entry_ids,
        "date_format_ok": date_format_ok,
        "bad_dates": bad_dates,
        "posting_id_format_ok": posting_id_format_ok,
        "posting_id_entry_id_ok": posting_id_entry_id_ok,
        "posting_id_line_no_ok": posting_id_line_no_ok,
        "bad_posting_ids": bad_posting_ids,
        "roots_seen": roots,
        "unknown_roots": unknown_roots,
        "notes": [
            "Raw delta uses (debit-credit). It must sum to 0 for a balanced ledger.",
            "Signed delta uses a normal-balance convention by root (Assets/Expenses debit-normal; Liabilities/Equity/Revenue credit-normal).",
        ],
        **(
            {
                "entry_id_policy": "generated",
                "generated_entry_ids": generated_entry_ids,
            }
            if cfg.entry_id_policy == "generated"
            else {}
        ),
    }


def gl_schema_description(cfg: LedgerEngineConfig | None = None) -> dict[str, Any]:
    """A tiny schema description for the GL tables (for docs/tooling)."""

    if cfg is None:
        dim_names = ["department"]
    else:
        dim_names = [d.name for d in cfg.effective_dimensions]

    dim_columns = [{"name": n, "type": "string"} for n in dim_names]

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
                    *dim_columns,
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
                    *[[n, "date"] for n in dim_names],
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

    The LedgerLoom engine is the *contract layer* between accounting ideas and
    software engineering practice:

    - Chapters are free to focus on pedagogy and artifacts.
    - The engine provides a single, tested implementation of conventions
      (normal balances, posting IDs, deterministic math).
    - Tests and invariants make refactors safe and keep outputs reproducible.

    Example
    -------
    >>> from ledgerloom.engine import LedgerEngine
    >>> eng = LedgerEngine()  # or LedgerEngine(cfg=...), LedgerEngine(config=...)
    >>> postings = eng.postings_fact_table(entries)

    v0.1 minimal API surface (methods): postings_fact_table, balances_by_* ,
    running_balance_by_posting, invariants, gl_schema_description.
    """

    cfg: LedgerEngineConfig = field(default_factory=LedgerEngineConfig)

    def __init__(
        self,
        cfg: LedgerEngineConfig | None = None,
        *,
        config: LedgerEngineConfig | None = None,
    ) -> None:
        """Create a LedgerEngine.

        ``config`` is accepted as an alias for ``cfg`` because it is the natural
        name many users will try first.
        """

        if cfg is not None and config is not None:
            raise TypeError("Provide only one of 'cfg' or 'config'.")
        chosen = cfg if cfg is not None else config
        if chosen is None:
            chosen = LedgerEngineConfig()
        object.__setattr__(self, "cfg", chosen)

    def postings_fact_table(self, entries: list[Entry]) -> pd.DataFrame:
        return postings_fact_table(entries, cfg=self.cfg)

    def validate_entries(self, entries: list[Entry]) -> None:
        """Run strict validation checks (does not mutate entries)."""

        validate_entries(entries, cfg=self.cfg)


    def balances_by_account(self, postings: pd.DataFrame) -> pd.DataFrame:
        return balances_by_account(postings, cfg=self.cfg)

    def balances_by_period(self, postings: pd.DataFrame) -> pd.DataFrame:
        return balances_by_period(postings)

    def balances_by_department(self, postings: pd.DataFrame) -> pd.DataFrame:
        return balances_by_department(postings)

    def balances_by_dimension(self, postings: pd.DataFrame, dimension: str) -> pd.DataFrame:
        return balances_by_dimension(postings, dimension=dimension)


    def postings_as_of(self, postings: pd.DataFrame, as_of: date | str) -> pd.DataFrame:
        """Filter postings to rows with ``date <= as_of``."""

        return postings_as_of(postings, as_of=as_of)

    def balances_by_account_as_of(self, postings: pd.DataFrame, as_of: date | str) -> pd.DataFrame:
        """Balances grouped by account, using postings up to ``as_of``."""

        return balances_by_account(postings_as_of(postings, as_of=as_of), cfg=self.cfg)

    def running_balance_by_posting(self, postings: pd.DataFrame) -> pd.DataFrame:
        return running_balance_by_posting(postings, cfg=self.cfg)

    def invariants(self, entries: list[Entry], postings: pd.DataFrame) -> dict[str, Any]:
        return invariants(entries, postings, cfg=self.cfg)

    def gl_schema_description(self) -> dict[str, Any]:
        return gl_schema_description(cfg=self.cfg)

"""Chart of Accounts (COA) loader + validation helpers.

LedgerLoom's engine already contains COA validation logic (:func:`ledgerloom.engine.coa.validate_accounts`).
For the "practical tool" workflow we also need a simple, versioned, human-editable
file format (YAML) that can be authored without touching Python.

This module implements that glue:

* Load a COA YAML file into :class:`ledgerloom.engine.coa.Account` objects.
* Provide a thin wrapper around the engine's COA validator.
* Provide a helper to check that referenced account codes exist.

YAML schema (v1)
--------------

The file is intentionally minimal and forgiving:

.. code-block:: yaml

    schema_id: ledgerloom.chart_of_accounts.v1
    accounts:
      - code: Assets:Cash
        name: Cash
        type: asset
      - code: Expenses:Meals
        name: Meals
        type: expense
      - code: Assets:AccumDep
        name: Accumulated Depreciation
        type: asset
        is_contra: true

Only ``code``, ``name``, and ``type`` are required per account.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from ledgerloom.engine.coa import Account, validate_accounts


COA_SCHEMA_ID_V1 = "ledgerloom.chart_of_accounts.v1"


@dataclass(frozen=True)
class CoaLoadResult:
    """Result of loading a COA file."""

    source_path: Path
    schema_id: str
    raw: dict[str, Any]
    accounts: list[Account]


def _parse_account_type(val: str, idx: int) -> str:
    """Normalize account type to one of: asset/liability/equity/revenue/expense."""

    norm = val.strip().lower().replace(" ", "_")
    aliases = {
        "asset": "asset",
        "assets": "asset",
        "liability": "liability",
        "liabilities": "liability",
        "equity": "equity",
        "revenue": "revenue",
        "income": "revenue",
        "expense": "expense",
        "expenses": "expense",
    }
    out = aliases.get(norm)
    if out is None:
        raise ValueError(
            f"accounts[{idx}].type must be one of asset/liability/equity/revenue/expense; got {val!r}"
        )
    return out


def _derive_expected_normal_side(account_type: str, is_contra: bool) -> str:
    # Mirrors ledgerloom.engine.coa.expected_side
    base = "debit" if account_type in {"asset", "expense"} else "credit"
    if is_contra:
        return "credit" if base == "debit" else "debit"
    return base


def _derive_expected_statement(account_type: str) -> str:
    # Mirrors ledgerloom.engine.coa.expected_stmt
    return "BS" if account_type in {"asset", "liability", "equity"} else "IS"


def _parse_normal_side(val: str, idx: int) -> str:
    norm = val.strip().lower()
    if norm not in {"debit", "credit"}:
        raise ValueError(f"accounts[{idx}].normal_side must be debit/credit; got {val!r}")
    return norm


def _parse_statement(val: str, idx: int) -> str:
    norm = val.strip().upper()
    if norm not in {"BS", "IS"}:
        raise ValueError(f"accounts[{idx}].statement must be BS/IS; got {val!r}")
    return norm


def load_chart_of_accounts(path: Path) -> CoaLoadResult:
    """Load a COA YAML file into engine Account objects.

    Raises:
        ValueError: If the YAML is invalid or missing required fields.
    """

    raw_obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_obj, dict):
        raise ValueError("COA YAML must be a mapping (top-level YAML dictionary).")

    payload: dict[str, Any] = raw_obj
    schema_id = str(payload.get("schema_id", "")).strip()
    if schema_id != COA_SCHEMA_ID_V1:
        raise ValueError(
            f"Unsupported COA schema_id {schema_id!r}; expected {COA_SCHEMA_ID_V1!r}"
        )

    accounts_raw = payload.get("accounts")
    if not isinstance(accounts_raw, list) or not accounts_raw:
        raise ValueError("COA YAML must include a non-empty 'accounts' list.")

    accounts: list[Account] = []
    for i, row in enumerate(accounts_raw):
        if not isinstance(row, dict):
            raise ValueError(f"accounts[{i}] must be a mapping (YAML dictionary).")

        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        # Allow either `type` (preferred) or `account_type` (engine wording)
        type_raw = row.get("type", row.get("account_type", ""))
        type_str = str(type_raw).strip()

        if not code:
            raise ValueError(f"accounts[{i}].code is required")
        if not name:
            raise ValueError(f"accounts[{i}].name is required")
        if not type_str:
            raise ValueError(f"accounts[{i}].type is required")

        account_type = _parse_account_type(type_str, i)

        is_contra = bool(row.get("is_contra", False))
        rollup_code = row.get("rollup_code")
        rollup_code = str(rollup_code).strip() if rollup_code else None

        # Defaults derived from account_type (+ contra), unless explicitly provided.
        normal_side_raw = row.get("normal_side")
        if normal_side_raw is None:
            normal_side = _derive_expected_normal_side(account_type, is_contra)
        else:
            normal_side = _parse_normal_side(str(normal_side_raw), i)

        statement_raw = row.get("statement")
        if statement_raw is None:
            statement = _derive_expected_statement(account_type)
        else:
            statement = _parse_statement(str(statement_raw), i)

        is_active = bool(row.get("is_active", True))
        track_department = bool(row.get("track_department", False))
        track_project = bool(row.get("track_project", False))
        description = row.get("description")
        description = str(description).strip() if description else None

        accounts.append(
            Account(
                code=code,
                name=name,
                account_type=account_type,
                normal_side=normal_side,
                statement=statement,
                rollup_code=rollup_code,
                is_contra=is_contra,
                is_active=is_active,
                track_department=track_department,
                track_project=track_project,
                description=description,
            )
        )

    return CoaLoadResult(
        source_path=path,
        schema_id=schema_id,
        raw=payload,
        accounts=accounts,
    )


def validate_coa(accounts: Sequence[Account]) -> list[str]:
    """Run engine COA validation checks.

    Returns:
        A list of human-readable check results.
    """

    return validate_accounts(accounts)


def missing_account_codes(accounts: Sequence[Account], referenced: Iterable[str]) -> list[str]:
    """Return a sorted list of referenced account codes not present in COA."""

    present = {a.code for a in accounts}
    missing = sorted({c for c in referenced if c not in present})
    return missing

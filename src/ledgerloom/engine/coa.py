"""Chart of Accounts (COA) engine primitives.

Chapter 03 introduces a COA as a *schema*:
- accounts as a dimension table (account master)
- rollups (parent/child) for reporting
- segments (department/project) as extra dimensions

The engine provides data structures + deterministic computations.
Chapters can write these out to CSV/JSON however they like.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Sequence

getcontext().prec = 28
D0 = Decimal("0")


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _d(x: str | int | Decimal) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def dec_str_2(x: Decimal) -> str:
    """Stable 2-decimal formatting; normalize -0.00 -> 0.00."""

    q = x.quantize(Decimal("0.01"))
    if q == D0:
        return "0.00"
    s = format(q, "f")
    if "." not in s:
        return f"{s}.00"
    whole, frac = s.split(".", 1)
    frac = (frac + "00")[:2]
    return f"{whole}.{frac}"


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    account_type: str  # asset/liability/equity/revenue/expense
    normal_side: str  # debit/credit
    statement: str  # BS or IS
    rollup_code: str  # parent / rollup bucket
    is_contra: bool
    is_active: bool
    track_department: bool
    track_project: bool
    description: str


@dataclass(frozen=True)
class SegmentValue:
    dimension_code: str  # DEPT or PROJ
    value_code: str
    value_name: str


def default_accounts() -> list[Account]:
    """A tiny but realistic default COA used in Chapter 03."""

    return [
        # Rollups (top-level)
        Account("1000", "Assets", "asset", "debit", "BS", "", False, True, False, False, "Rollup: all assets"),
        Account("2000", "Liabilities", "liability", "credit", "BS", "", False, True, False, False, "Rollup: all liabilities"),
        Account("3000", "Equity", "equity", "credit", "BS", "", False, True, False, False, "Rollup: all equity"),
        Account("4000", "Revenue", "revenue", "credit", "IS", "", False, True, True, True, "Rollup: all revenue"),
        Account("5000", "Expenses", "expense", "debit", "IS", "", False, True, True, True, "Rollup: all expenses"),
        # Asset detail
        Account("1100", "Cash", "asset", "debit", "BS", "1000", False, True, False, False, "Cash on hand / bank"),
        Account("1200", "Accounts Receivable", "asset", "debit", "BS", "1000", False, True, True, True, "Customer receivables (segment-tracked)"),
        Account("1300", "Inventory", "asset", "debit", "BS", "1000", False, True, True, True, "Inventory held for sale (segment-tracked)"),
        Account("1500", "Equipment", "asset", "debit", "BS", "1000", False, True, False, True, "Equipment (project-tracked)"),
        # Liability detail
        Account("2100", "Accounts Payable", "liability", "credit", "BS", "2000", False, True, True, True, "Supplier payables (segment-tracked)"),
        Account("2200", "Notes Payable", "liability", "credit", "BS", "2000", False, True, False, True, "Debt instruments (project-tracked)"),
        # Equity detail
        Account("3100", "Owner Capital", "equity", "credit", "BS", "3000", False, True, False, False, "Owner contributions"),
        Account("3200", "Retained Earnings", "equity", "credit", "BS", "3000", False, True, False, False, "Cumulative profits"),
        # Revenue detail
        Account("4100", "Sales Revenue", "revenue", "credit", "IS", "4000", False, True, True, True, "Product/service revenue"),
        Account("4200", "Service Revenue", "revenue", "credit", "IS", "4000", False, True, True, True, "Services revenue"),
        # Expense detail
        Account("5100", "COGS", "expense", "debit", "IS", "5000", False, True, True, True, "Cost of goods sold"),
        Account("5200", "Rent Expense", "expense", "debit", "IS", "5000", False, True, True, False, "Rent (dept-tracked)"),
        Account("5300", "Wages Expense", "expense", "debit", "IS", "5000", False, True, True, False, "Wages (dept-tracked)"),
        Account("5400", "Marketing Expense", "expense", "debit", "IS", "5000", False, True, True, True, "Marketing (segment-tracked)"),
        # Contra example
        Account("1510", "Accumulated Depreciation", "asset", "credit", "BS", "1000", True, True, False, True, "Contra-asset for equipment"),
    ]


def default_segments() -> tuple[list[dict[str, str]], list[SegmentValue]]:
    dims = [
        {
            "dimension_code": "DEPT",
            "dimension_name": "Department",
            "required": "false",
            "description": "Operational department (e.g., SALES, OPS).",
        },
        {
            "dimension_code": "PROJ",
            "dimension_name": "Project",
            "required": "false",
            "description": "Project / job / initiative (e.g., P001).",
        },
    ]
    values = [
        SegmentValue("DEPT", "SALES", "Sales"),
        SegmentValue("DEPT", "OPS", "Operations"),
        SegmentValue("PROJ", "P001", "Website Revamp"),
        SegmentValue("PROJ", "P002", "New Product Launch"),
    ]
    return dims, values


def schema_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "account_master": {
            "primary_key": ["code"],
            "fields": [
                {"name": "code", "type": "string", "pattern": r"^\d{4}$", "description": "Account code (4 digits)"},
                {"name": "name", "type": "string"},
                {"name": "account_type", "type": "enum", "values": ["asset", "liability", "equity", "revenue", "expense"]},
                {"name": "normal_side", "type": "enum", "values": ["debit", "credit"]},
                {"name": "statement", "type": "enum", "values": ["BS", "IS"], "description": "Balance Sheet / Income Statement"},
                {"name": "rollup_code", "type": "string", "nullable": True, "description": "Parent rollup bucket"},
                {"name": "is_contra", "type": "bool", "description": "Contra accounts invert the normal balance for presentation"},
                {"name": "is_active", "type": "bool"},
                {"name": "track_department", "type": "bool"},
                {"name": "track_project", "type": "bool"},
                {"name": "description", "type": "string"},
            ],
            "constraints": [
                "unique(code)",
                "rollup_code must reference an existing account or be empty",
                "no cycles in rollup relationships",
                "normal_side is debit for assets/expenses and credit for liabilities/equity/revenue (except contra accounts may differ)",
            ],
        },
        "segments": {
            "dimensions": [
                {"dimension_code": "DEPT", "description": "Department"},
                {"dimension_code": "PROJ", "description": "Project"},
            ],
            "rules": [
                "When an account has track_department=true, postings should include a DEPT value.",
                "When an account has track_project=true, postings should include a PROJ value.",
            ],
        },
    }


def validate_accounts(accounts: Sequence[Account]) -> list[str]:
    checks: list[str] = []

    codes = [a.code for a in accounts]
    if len(set(codes)) != len(codes):
        checks.append("FAIL: unique_codes — duplicate account codes found")
    else:
        checks.append("PASS: unique_codes — all account codes are unique")

    code_set = set(codes)
    bad_rollups = [a for a in accounts if a.rollup_code and a.rollup_code not in code_set]
    if bad_rollups:
        checks.append("FAIL: rollup_references — some rollup_code values do not exist")
        for a in bad_rollups[:10]:
            checks.append(f"  - {a.code} rollup_code={a.rollup_code}")
    else:
        checks.append("PASS: rollup_references — all rollup_code values reference an existing account (or empty)")

    parent = {a.code: a.rollup_code for a in accounts}

    def has_cycle(start: str) -> bool:
        seen = set()
        cur = start
        while cur and cur in parent:
            if cur in seen:
                return True
            seen.add(cur)
            cur = parent[cur]
        return False

    cycles = [c for c in codes if has_cycle(c)]
    if cycles:
        checks.append("FAIL: rollup_cycles — cycle(s) detected in rollup graph")
        for c in cycles[:10]:
            checks.append(f"  - {c}")
    else:
        checks.append("PASS: rollup_cycles — no cycles detected in rollup relationships")

    def expected_side(acct_type: str) -> str:
        if acct_type in {"asset", "expense"}:
            return "debit"
        return "credit"

    bad_side = []
    for a in accounts:
        exp = expected_side(a.account_type)
        if (not a.is_contra) and a.normal_side != exp:
            bad_side.append((a.code, a.account_type, a.normal_side, exp))
    if bad_side:
        checks.append("FAIL: normal_side_convention — non-contra accounts violating normal side convention")
        for c, t, ns, exp in bad_side[:10]:
            checks.append(f"  - {c}: type={t} normal_side={ns} expected={exp}")
    else:
        checks.append("PASS: normal_side_convention — normal sides match type conventions (non-contra)")

    def expected_stmt(acct_type: str) -> str:
        return "BS" if acct_type in {"asset", "liability", "equity"} else "IS"

    bad_stmt = []
    for a in accounts:
        exp = expected_stmt(a.account_type)
        if a.statement != exp:
            bad_stmt.append((a.code, a.account_type, a.statement, exp))
    if bad_stmt:
        checks.append("FAIL: statement_mapping — accounts mapped to wrong statement")
        for c, t, s, exp in bad_stmt[:10]:
            checks.append(f"  - {c}: type={t} statement={s} expected={exp}")
    else:
        checks.append("PASS: statement_mapping — statement mapping consistent with account types")

    return checks


def build_account_master_rows(accounts: Sequence[Account]) -> list[dict[str, str]]:
    rows = []
    for a in sorted(accounts, key=lambda x: x.code):
        rows.append(
            {
                "code": a.code,
                "name": a.name,
                "account_type": a.account_type,
                "normal_side": a.normal_side,
                "statement": a.statement,
                "rollup_code": a.rollup_code,
                "is_contra": "true" if a.is_contra else "false",
                "is_active": "true" if a.is_active else "false",
                "track_department": "true" if a.track_department else "false",
                "track_project": "true" if a.track_project else "false",
                "description": a.description,
            }
        )
    return rows


def canonical_master_hash(master_rows: Sequence[dict[str, str]]) -> str:
    cols = [
        "code",
        "name",
        "account_type",
        "normal_side",
        "statement",
        "rollup_code",
        "is_contra",
        "is_active",
        "track_department",
        "track_project",
        "description",
    ]
    lines = []
    for r in master_rows:
        lines.append("|".join(r.get(c, "") for c in cols))
    return sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def example_income_statement_by_department(seed: int) -> list[dict[str, str]]:
    """Tiny worked example: revenue + expenses by department."""

    rng = random.Random(seed)

    depts = ["SALES", "OPS"]
    rows = []
    for d in depts:
        rev = _d(rng.randint(9000, 14000))
        exp = _d(rng.randint(5000, 9000))
        net = rev - exp
        rows.append(
            {
                "dept": d,
                "revenue": dec_str_2(rev),
                "expenses": dec_str_2(exp),
                "net_income": dec_str_2(net),
            }
        )

    total_rev = sum(_d(r["revenue"]) for r in rows)
    total_exp = sum(_d(r["expenses"]) for r in rows)
    total_net = total_rev - total_exp
    rows.append(
        {
            "dept": "TOTAL",
            "revenue": dec_str_2(total_rev),
            "expenses": dec_str_2(total_exp),
            "net_income": dec_str_2(total_net),
        }
    )
    return rows


@dataclass(frozen=True)
class COASchema:
    """A COA schema bundle suitable for joins + validation."""

    accounts: tuple[Account, ...]
    segment_dimensions: tuple[dict[str, str], ...]
    segment_values: tuple[SegmentValue, ...]

    @staticmethod
    def default() -> "COASchema":
        dims, vals = default_segments()
        return COASchema(
            accounts=tuple(default_accounts()),
            segment_dimensions=tuple(dims),
            segment_values=tuple(vals),
        )

    def schema_dict(self) -> dict[str, object]:
        return schema_dict()

    def segment_value_rows(self) -> list[dict[str, str]]:
        return [
            {"dimension_code": v.dimension_code, "value_code": v.value_code, "value_name": v.value_name}
            for v in self.segment_values
        ]

    def account_master_rows(self) -> list[dict[str, str]]:
        return build_account_master_rows(self.accounts)

    def validate_checks(self) -> list[str]:
        return validate_accounts(self.accounts)

    def canonical_master_hash(self) -> str:
        return canonical_master_hash(self.account_master_rows())

    def example_income_statement_by_department(self, seed: int) -> list[dict[str, str]]:
        return example_income_statement_by_department(seed)

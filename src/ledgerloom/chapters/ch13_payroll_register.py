"""LedgerLoom Chapter 13 — Payroll as a multi-line event (register import).

Payroll is a great example of why LedgerLoom treats *journal entries as structured
accounting events*.

A single pay run touches multiple accounts:

- Wage expense (gross pay)
- Employee withholdings (tax + statutory deductions)
- Employer payroll taxes (expense + payable)
- Cash paid to employees (net pay)

This chapter demonstrates a practical workflow:

1) Import a payroll register export (CSV)
2) Convert each pay run into a deterministic, multi-line journal entry
3) Post cash payments to employees
4) Post statutory remittances (withholdings + employer contributions)
5) Reconcile the payroll register (subledger) to G/L control accounts

The goal is not to model every jurisdiction's rules — it is to show a clean,
inspectable pipeline where payroll data becomes ledger postings.
"""

from __future__ import annotations

import argparse
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


CHAPTER = "ch13"

# Keep the same simulated window as Chapters 09–12.
PERIOD_START = date(2026, 2, 1)
PERIOD_END = date(2026, 4, 30)
ASOF_DATE = PERIOD_END

# Accounts (free-form names; only the root segment is interpreted by the engine).
ACCT_WAGES = "Expenses:Payroll:Wages"
ACCT_EMP_TAXES = "Expenses:Payroll:EmployerTaxes"

ACCT_NET_PAY_PAYABLE = "Liabilities:Payroll:NetPayPayable"
ACCT_FED_WHT = "Liabilities:Payroll:Withholdings:Federal"
ACCT_PROV_WHT = "Liabilities:Payroll:Withholdings:Provincial"
ACCT_CPP_EE = "Liabilities:Payroll:CPPEmployee"
ACCT_EI_EE = "Liabilities:Payroll:EIEmployee"
ACCT_CPP_ER = "Liabilities:Payroll:CPPEmployer"
ACCT_EI_ER = "Liabilities:Payroll:EIEmployer"
ACCT_BEN_PAYABLE = "Liabilities:Payroll:BenefitsPayable"

ACCT_CASH = "Assets:Cash"


def _cents(i: int) -> Decimal:
    return Decimal(cents_to_str(i))


def _w_df(path: Path, df: pd.DataFrame) -> None:
    write_csv_df(path, df)


def _w_csv(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    write_csv_dicts(path, rows, fieldnames=cols)


def _w_json(path: Path, obj: Any) -> None:
    write_json(path, obj)


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
    return str_to_cents(str(row.iloc[0]["balance"]))


def _make_entry(
    *,
    entry_id: str,
    dt: date,
    narration: str,
    postings: list[Posting],
    meta: dict[str, str] | None = None,
) -> Entry:
    m = {"entry_id": entry_id, "chapter": CHAPTER}
    if meta:
        m.update(meta)

    e = Entry(dt=dt, narration=narration, postings=postings, meta=m)
    e.validate_balanced()
    return e


def _next_month(y: int, m: int) -> tuple[int, int]:
    if m == 12:
        return y + 1, 1
    return y, m + 1


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _remittance_date_for_month(month: str) -> date:
    """15th of the next month (simplified teaching rule)."""

    y, m = (int(x) for x in month.split("-", 1))
    y2, m2 = _next_month(y, m)
    return date(y2, m2, 15)


def _row(
    *,
    pay_run_id: str,
    pay_date: date,
    employee_id: str,
    employee_name: str,
    department: str,
    gross_cents: int,
    fed_cents: int,
    prov_cents: int,
    cpp_cents: int,
    ei_cents: int,
    benefits_cents: int,
    employer_cpp_cents: int,
    employer_ei_cents: int,
) -> dict[str, Any]:
    deductions = fed_cents + prov_cents + cpp_cents + ei_cents + benefits_cents
    net_cents = gross_cents - deductions
    if net_cents < 0:
        raise ValueError(f"Net pay is negative for {pay_run_id}/{employee_id}")

    return {
        "pay_run_id": pay_run_id,
        "pay_date": pay_date.isoformat(),
        "employee_id": employee_id,
        "employee_name": employee_name,
        "department": department,
        "gross_pay": cents_to_str(gross_cents),
        "federal_withholding": cents_to_str(fed_cents),
        "provincial_withholding": cents_to_str(prov_cents),
        "cpp_employee": cents_to_str(cpp_cents),
        "ei_employee": cents_to_str(ei_cents),
        "benefits_deduction": cents_to_str(benefits_cents),
        "net_pay": cents_to_str(net_cents),
        "employer_cpp": cents_to_str(employer_cpp_cents),
        "employer_ei": cents_to_str(employer_ei_cents),
    }


def _payroll_register_rows() -> list[dict[str, Any]]:
    """Deterministic toy payroll register export (two employees, biweekly)."""

    alice = {"employee_id": "E-100", "employee_name": "Alice Chen", "department": "Ops"}
    bob = {"employee_id": "E-200", "employee_name": "Bob Singh", "department": "Ops"}

    # Base amounts (cents)
    a_base = {
        "gross": 250_000,
        "fed": 32_000,
        "prov": 14_000,
        "cpp": 12_000,
        "ei": 4_000,
        "ben": 6_000,
        "cpp_er": 12_000,
        "ei_er": 5_600,
    }
    b_base = {
        "gross": 180_000,
        "fed": 22_000,
        "prov": 10_000,
        "cpp": 8_500,
        "ei": 3_000,
        "ben": 4_500,
        "cpp_er": 8_500,
        "ei_er": 4_200,
    }

    # Variations (show that real registers aren't perfectly constant)
    a_bonus = {
        "gross": 280_000,
        "fed": 36_000,
        "prov": 16_000,
        "cpp": 12_000,
        "ei": 4_500,
        "ben": 6_000,
        "cpp_er": 12_000,
        "ei_er": 6_300,
    }
    b_ot = {
        "gross": 195_000,
        "fed": 24_000,
        "prov": 11_000,
        "cpp": 9_000,
        "ei": 3_250,
        "ben": 4_500,
        "cpp_er": 9_000,
        "ei_er": 4_550,
    }

    a_raise = {
        "gross": 255_000,
        "fed": 32_500,
        "prov": 14_250,
        "cpp": 12_250,
        "ei": 4_100,
        "ben": 6_000,
        "cpp_er": 12_250,
        "ei_er": 5_740,
    }
    b_raise = {
        "gross": 185_000,
        "fed": 22_500,
        "prov": 10_250,
        "cpp": 8_750,
        "ei": 3_050,
        "ben": 4_500,
        "cpp_er": 8_750,
        "ei_er": 4_270,
    }

    runs: list[tuple[str, date, dict[str, int], dict[str, int]]] = [
        ("PR-2026-02-15", date(2026, 2, 15), a_base, b_base),
        ("PR-2026-02-28", date(2026, 2, 28), a_base, b_base),
        ("PR-2026-03-15", date(2026, 3, 15), a_base, b_base),
        ("PR-2026-03-31", date(2026, 3, 31), a_bonus, b_ot),
        ("PR-2026-04-15", date(2026, 4, 15), a_base, b_base),
        ("PR-2026-04-30", date(2026, 4, 30), a_raise, b_raise),
    ]

    rows: list[dict[str, Any]] = []
    for run_id, d, a, b in runs:
        rows.append(
            _row(
                pay_run_id=run_id,
                pay_date=d,
                **alice,
                gross_cents=a["gross"],
                fed_cents=a["fed"],
                prov_cents=a["prov"],
                cpp_cents=a["cpp"],
                ei_cents=a["ei"],
                benefits_cents=a["ben"],
                employer_cpp_cents=a["cpp_er"],
                employer_ei_cents=a["ei_er"],
            )
        )
        rows.append(
            _row(
                pay_run_id=run_id,
                pay_date=d,
                **bob,
                gross_cents=b["gross"],
                fed_cents=b["fed"],
                prov_cents=b["prov"],
                cpp_cents=b["cpp"],
                ei_cents=b["ei"],
                benefits_cents=b["ben"],
                employer_cpp_cents=b["cpp_er"],
                employer_ei_cents=b["ei_er"],
            )
        )

    # Stable output order.
    rows = sorted(rows, key=lambda r: (str(r["pay_date"]), str(r["employee_id"])))
    return rows


def run(outdir: Path, seed: int = 123) -> Path:
    _ = seed  # deterministic chapter; seed kept for CLI consistency

    cfg = LedgerEngineConfig()
    engine = LedgerEngine(cfg=cfg)

    out_ch = outdir / CHAPTER
    out_ch.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1) Start from Chapter 08 post-close, then create an opening entry
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
    # 2) Import payroll register CSV (toy export)
    # ------------------------------------------------------------------
    register_rows = _payroll_register_rows()
    reg_df = pd.DataFrame(register_rows)

    # Convert money strings to cents for computation.
    money_cols = [
        "gross_pay",
        "federal_withholding",
        "provincial_withholding",
        "cpp_employee",
        "ei_employee",
        "benefits_deduction",
        "net_pay",
        "employer_cpp",
        "employer_ei",
    ]
    reg_c = reg_df.copy()
    for c in money_cols:
        reg_c[c + "_cents"] = reg_c[c].map(lambda x: str_to_cents(str(x)))

    # Validate register arithmetic (gross - deductions == net).
    deductions = (
        reg_c["federal_withholding_cents"]
        + reg_c["provincial_withholding_cents"]
        + reg_c["cpp_employee_cents"]
        + reg_c["ei_employee_cents"]
        + reg_c["benefits_deduction_cents"]
    )
    computed_net = reg_c["gross_pay_cents"] - deductions
    if not (computed_net == reg_c["net_pay_cents"]).all():
        bad = reg_c.loc[computed_net != reg_c["net_pay_cents"], ["pay_run_id", "employee_id", "gross_pay", "net_pay"]]
        raise ValueError(f"Payroll register net pay mismatch:\n{bad.to_string(index=False)}")

    reg_c["pay_date_dt"] = reg_c["pay_date"].map(lambda s: date.fromisoformat(str(s)))
    reg_c["month"] = reg_c["pay_date_dt"].map(_month_key)

    # Summarize to pay-run totals (one journal entry per pay run)
    run_totals = (
        reg_c.groupby(["pay_run_id", "pay_date"], sort=True, as_index=False)
        .agg(
            employees=("employee_id", "nunique"),
            gross_pay_cents=("gross_pay_cents", "sum"),
            federal_withholding_cents=("federal_withholding_cents", "sum"),
            provincial_withholding_cents=("provincial_withholding_cents", "sum"),
            cpp_employee_cents=("cpp_employee_cents", "sum"),
            ei_employee_cents=("ei_employee_cents", "sum"),
            benefits_deduction_cents=("benefits_deduction_cents", "sum"),
            net_pay_cents=("net_pay_cents", "sum"),
            employer_cpp_cents=("employer_cpp_cents", "sum"),
            employer_ei_cents=("employer_ei_cents", "sum"),
        )
        .sort_values(["pay_date", "pay_run_id"], kind="mergesort")
        .reset_index(drop=True)
    )

    run_summary_rows: list[dict[str, Any]] = []
    for _, r in run_totals.iterrows():
        employer_total = int(r["employer_cpp_cents"] + r["employer_ei_cents"])
        run_summary_rows.append(
            {
                "pay_run_id": str(r["pay_run_id"]),
                "pay_date": str(r["pay_date"]),
                "employees": int(r["employees"]),
                "gross_pay": cents_to_str(int(r["gross_pay_cents"])),
                "employee_withholdings": cents_to_str(
                    int(
                        r["federal_withholding_cents"]
                        + r["provincial_withholding_cents"]
                        + r["cpp_employee_cents"]
                        + r["ei_employee_cents"]
                    )
                ),
                "benefits_deduction": cents_to_str(int(r["benefits_deduction_cents"])),
                "net_pay": cents_to_str(int(r["net_pay_cents"])),
                "employer_taxes": cents_to_str(employer_total),
            }
        )

    # Remittance schedule (teaching rule): remit on the 15th of next month.
    month_totals = (
        reg_c.groupby(["month"], sort=True, as_index=False)
        .agg(
            federal_withholding_cents=("federal_withholding_cents", "sum"),
            provincial_withholding_cents=("provincial_withholding_cents", "sum"),
            cpp_employee_cents=("cpp_employee_cents", "sum"),
            ei_employee_cents=("ei_employee_cents", "sum"),
            benefits_deduction_cents=("benefits_deduction_cents", "sum"),
            employer_cpp_cents=("employer_cpp_cents", "sum"),
            employer_ei_cents=("employer_ei_cents", "sum"),
        )
        .sort_values(["month"], kind="mergesort")
        .reset_index(drop=True)
    )

    remittance_rows: list[dict[str, Any]] = []
    remittance_months_posted: list[str] = []
    for _, r in month_totals.iterrows():
        month = str(r["month"])
        remit_date = _remittance_date_for_month(month)
        total_cents = int(
            r["federal_withholding_cents"]
            + r["provincial_withholding_cents"]
            + r["cpp_employee_cents"]
            + r["ei_employee_cents"]
            + r["employer_cpp_cents"]
            + r["employer_ei_cents"]
            + r["benefits_deduction_cents"]
        )
        posted = remit_date <= PERIOD_END
        if posted:
            remittance_months_posted.append(month)

        remittance_rows.append(
            {
                "month": month,
                "remittance_date": remit_date.isoformat(),
                "posted_in_period": "yes" if posted else "no",
                "federal_withholding": cents_to_str(int(r["federal_withholding_cents"])),
                "provincial_withholding": cents_to_str(int(r["provincial_withholding_cents"])),
                "cpp_employee": cents_to_str(int(r["cpp_employee_cents"])),
                "ei_employee": cents_to_str(int(r["ei_employee_cents"])),
                "cpp_employer": cents_to_str(int(r["employer_cpp_cents"])),
                "ei_employer": cents_to_str(int(r["employer_ei_cents"])),
                "benefits": cents_to_str(int(r["benefits_deduction_cents"])),
                "total_cash": cents_to_str(total_cents),
            }
        )

    # ------------------------------------------------------------------
    # 3) Translate register -> G/L entries
    # ------------------------------------------------------------------
    entries_new: list[Entry] = []

    # Payroll run entries (accrual) + employee net pay payments
    for _, r in run_totals.iterrows():
        pay_run_id = str(r["pay_run_id"])
        pay_date = date.fromisoformat(str(r["pay_date"]))

        gross = int(r["gross_pay_cents"])
        fed = int(r["federal_withholding_cents"])
        prov = int(r["provincial_withholding_cents"])
        cpp_ee = int(r["cpp_employee_cents"])
        ei_ee = int(r["ei_employee_cents"])
        ben = int(r["benefits_deduction_cents"])
        net = int(r["net_pay_cents"])
        cpp_er = int(r["employer_cpp_cents"])
        ei_er = int(r["employer_ei_cents"])
        employer_total = cpp_er + ei_er

        entries_new.append(
            _make_entry(
                entry_id=f"payrun:{pay_run_id}",
                dt=pay_date,
                narration=f"Payroll run {pay_run_id} ({pay_date.isoformat()})",
                postings=[
                    Posting(ACCT_WAGES, debit=_cents(gross), credit=Decimal("0")),
                    Posting(ACCT_EMP_TAXES, debit=_cents(employer_total), credit=Decimal("0")),
                    Posting(ACCT_FED_WHT, debit=Decimal("0"), credit=_cents(fed)),
                    Posting(ACCT_PROV_WHT, debit=Decimal("0"), credit=_cents(prov)),
                    Posting(ACCT_CPP_EE, debit=Decimal("0"), credit=_cents(cpp_ee)),
                    Posting(ACCT_EI_EE, debit=Decimal("0"), credit=_cents(ei_ee)),
                    Posting(ACCT_BEN_PAYABLE, debit=Decimal("0"), credit=_cents(ben)),
                    Posting(ACCT_CPP_ER, debit=Decimal("0"), credit=_cents(cpp_er)),
                    Posting(ACCT_EI_ER, debit=Decimal("0"), credit=_cents(ei_er)),
                    Posting(ACCT_NET_PAY_PAYABLE, debit=Decimal("0"), credit=_cents(net)),
                ],
                meta={"entry_kind": "payroll_run", "pay_run_id": pay_run_id, "source": "payroll_register.csv"},
            )
        )

        entries_new.append(
            _make_entry(
                entry_id=f"paynet:{pay_run_id}",
                dt=pay_date,
                narration=f"Pay employees net wages for {pay_run_id}",
                postings=[
                    Posting(ACCT_NET_PAY_PAYABLE, debit=_cents(net), credit=Decimal("0")),
                    Posting(ACCT_CASH, debit=Decimal("0"), credit=_cents(net)),
                ],
                meta={"entry_kind": "employee_payment", "pay_run_id": pay_run_id},
            )
        )

    # Statutory remittances (withholdings + employer contributions + benefits)
    for rr in remittance_rows:
        if rr["posted_in_period"] != "yes":
            continue

        month = str(rr["month"])
        remit_date = date.fromisoformat(str(rr["remittance_date"]))

        fed = str_to_cents(str(rr["federal_withholding"]))
        prov = str_to_cents(str(rr["provincial_withholding"]))
        cpp_ee = str_to_cents(str(rr["cpp_employee"]))
        ei_ee = str_to_cents(str(rr["ei_employee"]))
        cpp_er = str_to_cents(str(rr["cpp_employer"]))
        ei_er = str_to_cents(str(rr["ei_employer"]))
        ben = str_to_cents(str(rr["benefits"]))

        total = fed + prov + cpp_ee + ei_ee + cpp_er + ei_er + ben

        entries_new.append(
            _make_entry(
                entry_id=f"remit:{month}",
                dt=remit_date,
                narration=f"Remit payroll withholdings and contributions for {month}",
                postings=[
                    Posting(ACCT_FED_WHT, debit=_cents(fed), credit=Decimal("0")),
                    Posting(ACCT_PROV_WHT, debit=_cents(prov), credit=Decimal("0")),
                    Posting(ACCT_CPP_EE, debit=_cents(cpp_ee), credit=Decimal("0")),
                    Posting(ACCT_EI_EE, debit=_cents(ei_ee), credit=Decimal("0")),
                    Posting(ACCT_CPP_ER, debit=_cents(cpp_er), credit=Decimal("0")),
                    Posting(ACCT_EI_ER, debit=_cents(ei_er), credit=Decimal("0")),
                    Posting(ACCT_BEN_PAYABLE, debit=_cents(ben), credit=Decimal("0")),
                    Posting(ACCT_CASH, debit=Decimal("0"), credit=_cents(total)),
                ],
                meta={"entry_kind": "remittance", "month": month},
            )
        )

    # Build posting tables
    entries_all = [opening_entry, *entries_new]
    postings_all = engine.postings_fact_table(entries_all)

    new_entry_ids = {str(e.meta["entry_id"]) for e in entries_new}
    postings_payroll = postings_all.loc[postings_all["entry_id"].isin(sorted(new_entry_ids))].copy()

    tb_end = _tb(postings_all)
    is_current = _is(tb_end)
    bs_current = _bs(tb_end)

    # ------------------------------------------------------------------
    # 4) Controls and invariants
    # ------------------------------------------------------------------
    # Expected liability balances at period end = amounts for months whose remittance
    # date is after PERIOD_END (April in this scenario).
    outstanding_months = [
        rr["month"]
        for rr in remittance_rows
        if date.fromisoformat(str(rr["remittance_date"])) > PERIOD_END
    ]

    exp = {
        ACCT_FED_WHT: 0,
        ACCT_PROV_WHT: 0,
        ACCT_CPP_EE: 0,
        ACCT_EI_EE: 0,
        ACCT_CPP_ER: 0,
        ACCT_EI_ER: 0,
        ACCT_BEN_PAYABLE: 0,
        ACCT_NET_PAY_PAYABLE: 0,
    }

    for _, r in reg_c.iterrows():
        if str(r["month"]) not in outstanding_months:
            continue
        exp[ACCT_FED_WHT] += int(r["federal_withholding_cents"])
        exp[ACCT_PROV_WHT] += int(r["provincial_withholding_cents"])
        exp[ACCT_CPP_EE] += int(r["cpp_employee_cents"])
        exp[ACCT_EI_EE] += int(r["ei_employee_cents"])
        exp[ACCT_CPP_ER] += int(r["employer_cpp_cents"])
        exp[ACCT_EI_ER] += int(r["employer_ei_cents"])
        exp[ACCT_BEN_PAYABLE] += int(r["benefits_deduction_cents"])

    control_rows: list[dict[str, Any]] = []
    all_ok = True
    for acct in [
        ACCT_FED_WHT,
        ACCT_PROV_WHT,
        ACCT_CPP_EE,
        ACCT_EI_EE,
        ACCT_CPP_ER,
        ACCT_EI_ER,
        ACCT_BEN_PAYABLE,
        ACCT_NET_PAY_PAYABLE,
    ]:
        gl = _gl_balance_cents(tb_end, acct)
        expected = exp[acct]
        diff = gl - expected
        if diff != 0:
            all_ok = False
        control_rows.append(
            {
                "account": acct,
                "expected_subledger_balance": cents_to_str(expected),
                "gl_balance": cents_to_str(gl),
                "diff": cents_to_str(diff),
            }
        )

    control_df = pd.DataFrame(control_rows)

    # Expense reconciliation (starting from an opening TB with no expenses)
    exp_wages = int(reg_c["gross_pay_cents"].sum())
    exp_emp_taxes = int((reg_c["employer_cpp_cents"] + reg_c["employer_ei_cents"]).sum())

    gl_wages = _gl_balance_cents(tb_end, ACCT_WAGES)
    gl_emp_taxes = _gl_balance_cents(tb_end, ACCT_EMP_TAXES)

    # Cash outflows to employees and remittances (sum of cash credits)
    cash_postings = postings_payroll.loc[postings_payroll["account"] == ACCT_CASH].copy()
    cash_credits = int(cash_postings["credit"].map(lambda x: str_to_cents(str(x))).sum())

    exp_net_paid = int(reg_c["net_pay_cents"].sum())
    exp_remit_paid = sum(str_to_cents(str(rr["total_cash"])) for rr in remittance_rows if rr["posted_in_period"] == "yes")

    inv = engine.invariants(entries_all, postings_all)
    inv["checks"] = {
        "payroll_liability_control_reconciles": {
            "ok": all_ok,
            "asof": ASOF_DATE.isoformat(),
            "outstanding_months": outstanding_months,
        },
        "payroll_expenses_match_register": {
            "ok": (gl_wages == exp_wages) and (gl_emp_taxes == exp_emp_taxes),
            "gl_wages": cents_to_str(gl_wages),
            "reg_wages": cents_to_str(exp_wages),
            "gl_employer_taxes": cents_to_str(gl_emp_taxes),
            "reg_employer_taxes": cents_to_str(exp_emp_taxes),
        },
        "net_pay_payable_clears": {
            "ok": _gl_balance_cents(tb_end, ACCT_NET_PAY_PAYABLE) == 0,
            "gl_balance": cents_to_str(_gl_balance_cents(tb_end, ACCT_NET_PAY_PAYABLE)),
        },
        "cash_outflows_match_register_and_remittances": {
            "ok": cash_credits == exp_net_paid + exp_remit_paid,
            "cash_credits": cents_to_str(cash_credits),
            "expected": cents_to_str(exp_net_paid + exp_remit_paid),
        },
    }

    checklist = {
        "chapter": CHAPTER,
        "period_start": PERIOD_START.isoformat(),
        "period_end": PERIOD_END.isoformat(),
        "pay_runs": int(run_totals["pay_run_id"].nunique()),
        "employees": int(reg_c["employee_id"].nunique()),
        "register_rows": int(len(reg_c)),
        "remittances_posted": remittance_months_posted,
        "outstanding_months": outstanding_months,
        "liability_control_reconciles": all_ok,
        "limitations": [
            "Toy numbers (not jurisdiction-specific payroll rules).",
            "Remittance schedule is simplified (15th of next month).",
            "No benefits provider subledger; benefits are treated as a single payable.",
        ],
    }

    # ------------------------------------------------------------------
    # 5) Write artifacts + manifest
    # ------------------------------------------------------------------
    _w_df(out_ch / "postings_post_close.csv", postings_post_close)
    _w_df(out_ch / "trial_balance_post_close.csv", tb_post_close)
    _w_df(out_ch / "postings_opening.csv", postings_opening)
    _w_df(out_ch / "trial_balance_opening.csv", tb_opening)
    _w_df(out_ch / "reconciliation_post_close_vs_opening.csv", recon_df)

    _w_csv(
        out_ch / "payroll_register.csv",
        register_rows,
        [
            "pay_run_id",
            "pay_date",
            "employee_id",
            "employee_name",
            "department",
            "gross_pay",
            "federal_withholding",
            "provincial_withholding",
            "cpp_employee",
            "ei_employee",
            "benefits_deduction",
            "net_pay",
            "employer_cpp",
            "employer_ei",
        ],
    )
    _w_csv(
        out_ch / "payroll_runs_summary.csv",
        run_summary_rows,
        [
            "pay_run_id",
            "pay_date",
            "employees",
            "gross_pay",
            "employee_withholdings",
            "benefits_deduction",
            "net_pay",
            "employer_taxes",
        ],
    )
    _w_csv(
        out_ch / "payroll_remittances.csv",
        remittance_rows,
        [
            "month",
            "remittance_date",
            "posted_in_period",
            "federal_withholding",
            "provincial_withholding",
            "cpp_employee",
            "ei_employee",
            "cpp_employer",
            "ei_employer",
            "benefits",
            "total_cash",
        ],
    )

    _w_df(out_ch / "postings_payroll.csv", postings_payroll)
    _w_df(out_ch / "payroll_control_reconciliation.csv", control_df)

    _w_df(out_ch / "trial_balance_end_period.csv", tb_end)
    _w_df(out_ch / "income_statement_current_period.csv", is_current)
    _w_df(out_ch / "balance_sheet_current_period.csv", bs_current)

    _w_json(out_ch / "invariants.json", inv)
    _w_json(out_ch / "payroll_checklist.json", checklist)

    artifact_names = [
        "postings_post_close.csv",
        "trial_balance_post_close.csv",
        "postings_opening.csv",
        "trial_balance_opening.csv",
        "reconciliation_post_close_vs_opening.csv",
        "payroll_register.csv",
        "payroll_runs_summary.csv",
        "payroll_remittances.csv",
        "postings_payroll.csv",
        "payroll_control_reconciliation.csv",
        "trial_balance_end_period.csv",
        "income_statement_current_period.csv",
        "balance_sheet_current_period.csv",
        "invariants.json",
        "payroll_checklist.json",
    ]
    # Trust artifacts (run_meta.json + manifest.json)
    run_meta = {
        'chapter': CHAPTER,
        'module': 'ledgerloom.chapters.ch13_payroll_register',
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

    ch_dir = run(outdir=args.outdir, seed=args.seed)
    print(f"Wrote LedgerLoom Chapter 13 artifacts -> {ch_dir}")


if __name__ == "__main__":
    main()

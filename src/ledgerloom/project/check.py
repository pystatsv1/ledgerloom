"""Project-level *staging + validation* workflow.

This module powers the highest-value "practical tool" command:

``ledgerloom check``

The goal is to prevent the classic "Crash on Entry 500" frustration by
front-loading the most common problems into a human-readable report and a
machine-readable issues table.

Outputs
-------
The check workflow writes four artifacts into an output directory:

* ``checks.md`` – A human-readable summary (what to fix first).
* ``staging.csv`` – The normalized staging table (one row per staged entry).
* ``staging_issues.csv`` – Row-level issues (errors + warnings).
* ``unmapped.csv`` – Rows that posted to suspense (no mapping rule matched), with copy/paste mapping suggestions.

Important UX detail
-------------------
``source_row_number`` is **1-based relative to the first data row** in the
source CSV (i.e., it does not count the header). This is the number a user can
use to locate the record quickly in Excel / Google Sheets.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from ledgerloom.artifacts import write_csv_df, write_text
from ledgerloom.ingest.csv_bank_feed import ingest_bank_feed_csv
from ledgerloom.project.coa import load_chart_of_accounts
from ledgerloom.project.config import ProjectConfig
from ledgerloom.project.reclass import RECLASS_TEMPLATE_COLUMNS, reclass_template_from_unmapped


Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class CheckIssue:
    """A single staging/check issue.

    ``source_row_number`` is the original row number from the source CSV
    (1-based, header excluded).
    """

    severity: Severity
    code: str
    message: str

    source_name: str | None = None
    source_file: str | None = None
    source_row_number: int | None = None

    column: str | None = None
    raw_value: str | None = None
    account: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "source_name": self.source_name,
            "source_file": self.source_file,
            "source_row_number": self.source_row_number,
            "column": self.column,
            "raw_value": self.raw_value,
            "account": self.account,
        }


@dataclass(frozen=True)
class CheckResult:
    outdir: Path
    staging: pd.DataFrame
    issues: list[CheckIssue]

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def _resolve_inputs_dir(project_root: Path, cfg: ProjectConfig, inputs_dir: Path | None) -> Path:
    if inputs_dir is not None:
        return inputs_dir
    # Align with v0.2.0 practical-tool UX: inputs/<period>/
    return project_root / "inputs" / cfg.project.period


def _default_outdir(project_root: Path, cfg: ProjectConfig) -> Path:
    return project_root / cfg.outputs.root / "check" / cfg.project.period


def _issue_sort_key(i: CheckIssue) -> tuple[Any, ...]:
    """Stable ordering for issue lists and CSVs (determinism + UX)."""
    return (
        i.severity,
        i.source_name or "",
        i.source_file or "",
        i.source_row_number or 0,
        i.column or "",
        i.code,
        i.message,
    )


def _render_checks_md(
    *,
    project_root: Path,
    cfg: ProjectConfig,
    inputs_dir: Path,
    input_files: list[Path],
    staging: pd.DataFrame,
    issues: list[CheckIssue],
) -> str:
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    lines: list[str] = []
    lines.append("# LedgerLoom check")
    lines.append("")
    lines.append(f"- Project: **{cfg.project.name}**")
    lines.append(f"- Period: **{cfg.project.period}**")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    try:
        inputs_display = inputs_dir.relative_to(project_root).as_posix()
    except ValueError:
        # Avoid embedding machine-specific absolute paths in trust-affecting artifacts.
        inputs_display = inputs_dir.name
    lines.append(f"- Inputs directory: `{inputs_display}`")
    if input_files:
        for p in input_files:
            lines.append(f"- `{p.name}`")
    else:
        lines.append("- *(No input files matched the configured sources.)*")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Staged entries: **{len(staging)}**")
    lines.append(f"- Errors: **{len(errors)}**")
    lines.append(f"- Warnings: **{len(warnings)}**")
    unmapped_n = sum(1 for i in issues if i.code == "unmapped_suspense")
    lines.append(f"- Unmapped (suspense): **{unmapped_n}** (see `unmapped.csv`)")
    lines.append("")

    def _fmt_issue(i: CheckIssue) -> str:
        loc = ""
        if i.source_file and i.source_row_number is not None:
            loc = f" ({i.source_file} row {i.source_row_number})"
        elif i.source_row_number is not None:
            loc = f" (row {i.source_row_number})"
        return f"- **{i.code}**{loc}: {i.message}"

    if errors:
        lines.append("## Errors (fix these)")
        lines.append("")
        for i in errors[:50]:
            lines.append(_fmt_issue(i))
        if len(errors) > 50:
            lines.append(f"- *(…and {len(errors) - 50} more errors; see `staging_issues.csv`.)*")
        lines.append("")

    if warnings:
        lines.append("## Warnings (review)")
        lines.append("")
        for i in warnings[:50]:
            lines.append(_fmt_issue(i))
        if len(warnings) > 50:
            lines.append(
                f"- *(…and {len(warnings) - 50} more warnings; see `staging_issues.csv`.)*"
            )
        lines.append("")

    lines.append("## Files written")
    lines.append("")
    lines.append("- `checks.md` – this report")
    lines.append("- `staging.csv` – normalized staging table")
    lines.append("- `staging_issues.csv` – row-level issues (includes original row numbers)")
    lines.append("")
    lines.append(
        "**Note:** `source_row_number` is 1-based relative to the first data row in the source CSV (header excluded)."
    )
    lines.append("")
    return "\n".join(lines)


def _yaml_single_quote(value: str) -> str:
    """Return a YAML single-quoted scalar, escaping internal quotes.

    Using single quotes keeps the suggestion stable and easy to paste into YAML.
    """
    return "'" + value.replace("'", "''") + "'"


def _suggest_pattern_from_description(description: str) -> str:
    """Generate a conservative, copy/paste-friendly regex pattern.

    Heuristics (intentionally minimal):
    - collapse whitespace
    - replace digit runs with ``\\d+`` (helps with transaction IDs)
    - escape everything else
    - make it case-insensitive via ``(?i)``
    """
    desc = (description or "").strip()
    desc = re.sub(r"\s+", " ", desc)
    if not desc:
        return ""
    # Replace digit runs with a token, escape, then restore token to \d+
    token = "{NUM}"
    desc = re.sub(r"\d+", token, desc)
    esc = re.escape(desc)
    esc = esc.replace(re.escape(token), r"\d+")
    esc = esc.replace(r"\ ", r"\s+")
    return f"(?i){esc}"


def _suggest_account_hint(original_amount: Any) -> str:
    """Suggest a coarse account *category* hint based on amount sign.

    This is deliberately non-prescriptive; users should replace REPLACE_ME.
    """
    if original_amount is None:
        return "Expenses:REPLACE_ME"
    try:
        amt = Decimal(str(original_amount))
    except (InvalidOperation, ValueError):
        return "Expenses:REPLACE_ME"
    return "Revenue:REPLACE_ME" if amt > 0 else "Expenses:REPLACE_ME"


def _suggest_rule_yaml(pattern: str, account_hint: str) -> str:
    """Return a one-line YAML rule snippet the user can paste under ``rules:``."""
    pat_q = _yaml_single_quote(pattern)
    acct_q = _yaml_single_quote(account_hint)
    return f"- {{ pattern: {pat_q}, account: {acct_q} }}"



def run_check(
    *,
    project_root: Path,
    config_path: Path | None = None,
    inputs_dir: Path | None = None,
    outdir: Path | None = None,
) -> CheckResult:
    """Run staging + validation and write check artifacts.

    Parameters
    ----------
    project_root:
        Directory containing ``ledgerloom.yaml`` and project folders.
    config_path:
        Optional config path. If relative, it is resolved under ``project_root``.
    inputs_dir:
        Optional inputs directory override.
    outdir:
        Optional output directory override.
    """

    project_root = project_root.resolve()
    cfg_file = (project_root / "ledgerloom.yaml") if config_path is None else config_path
    if not cfg_file.is_absolute():
        cfg_file = project_root / cfg_file

    issues: list[CheckIssue] = []

    try:
        cfg = ProjectConfig.load_yaml(cfg_file)
    except Exception as e:  # pragma: no cover (exercise via CLI in integration tests)
        issues.append(CheckIssue(severity="error", code="config_load", message=str(e)))
        empty = pd.DataFrame()
        out = (project_root / "outputs" / "check") if outdir is None else outdir
        out.mkdir(parents=True, exist_ok=True)
        write_text(out / "checks.md", f"# LedgerLoom check\n\nConfig load failed: {e}\n")
        write_csv_df(out / "staging.csv", empty)
        write_csv_df(out / "staging_issues.csv", pd.DataFrame([i.to_dict() for i in issues]))
        return CheckResult(outdir=out, staging=empty, issues=issues)

    inputs_dir = _resolve_inputs_dir(project_root, cfg, inputs_dir)
    outdir = _default_outdir(project_root, cfg) if outdir is None else outdir
    outdir.mkdir(parents=True, exist_ok=True)

    # Load COA
    coa_path = project_root / cfg.chart_of_accounts
    try:
        coa = load_chart_of_accounts(coa_path)
        coa_codes = {a.code for a in coa.accounts}
    except Exception as e:
        issues.append(
            CheckIssue(
                severity="error",
                code="coa_load",
                message=f"Could not load chart of accounts: {e}",
            )
        )
        coa_codes = set()

    staged_rows: list[dict[str, Any]] = []
    unmapped_rows: list[dict[str, Any]] = []
    input_files: list[Path] = []

    if not inputs_dir.exists():
        issues.append(
            CheckIssue(
                severity="warning",
                code="inputs_missing",
                message=f"Inputs directory does not exist: {inputs_dir}",
            )
        )

    # Ingest per source and file.
    for src in cfg.sources:
        # Deterministic file ordering.
        files = sorted(inputs_dir.glob(src.file_pattern)) if inputs_dir.exists() else []
        if not files:
            issues.append(
                CheckIssue(
                    severity="warning",
                    code="no_files",
                    message=f"No files matched pattern {src.file_pattern!r} for source {src.name!r}",
                    source_name=src.name,
                )
            )
            continue

        for p in files:
            input_files.append(p)
            result = ingest_bank_feed_csv(p, src, strict=False)

            for iss in result.issues:
                issues.append(
                    CheckIssue(
                        severity="error",
                        code=iss.code,
                        message=iss.message,
                        source_name=src.name,
                        source_file=p.name,
                        source_row_number=iss.row_number,
                        column=iss.column,
                        raw_value=iss.raw_value,
                    )
                )

            for e in result.entries:
                meta = e.meta or {}
                row_number = meta.get("row_number")
                try:
                    row_number_int = int(row_number) if row_number is not None else None
                except Exception:
                    row_number_int = None

                # Bank-feed adapter produces two postings. Capture the debit/credit legs.
                # ``Posting.debit``/``Posting.credit`` are always Decimals; identify legs by > 0.
                debit_post = next((p for p in e.postings if p.debit > 0), None)
                credit_post = next((p for p in e.postings if p.credit > 0), None)

                debit_account = None if debit_post is None else debit_post.account
                credit_account = None if credit_post is None else credit_post.account

                amount = None
                if debit_post is not None:
                    amount = debit_post.debit
                elif credit_post is not None:
                    amount = credit_post.credit

                row_out = {
                        "entry_id": meta.get("entry_id"),
                        "date": e.dt.isoformat(),
                        "narration": e.narration,
                        "amount": str(amount) if amount is not None else None,
                        "debit_account": debit_account,
                        "credit_account": credit_account,
                        "source_type": meta.get("source_type"),
                        "source_name": meta.get("source_name"),
                        "source_file": meta.get("source_file"),
                        "source_row_number": row_number_int,
                        "matched_rule_pattern": meta.get("matched_rule_pattern"),
                        "original_description": meta.get("original_description"),
                        "original_amount": meta.get("original_amount"),
                }
                staged_rows.append(row_out)

                # Capture suspense postings so users can author mappings.
                if row_out.get("matched_rule_pattern") in (None, "", "None") and row_out.get("original_description") is not None:
                    desc = str(row_out.get("original_description") or "")
                    suggested_pattern = _suggest_pattern_from_description(desc)
                    suggested_account = _suggest_account_hint(row_out.get("original_amount"))
                    suggested_rule_yaml = (
                        _suggest_rule_yaml(suggested_pattern, suggested_account) if suggested_pattern else ""
                    )

                    unmapped_rows.append({
                        "entry_id": row_out.get("entry_id"),
                        "date": row_out.get("date"),
                        "source_name": row_out.get("source_name"),
                        "source_file": row_out.get("source_file"),
                        "source_row_number": row_out.get("source_row_number"),
                        "original_description": row_out.get("original_description"),
                        "original_amount": row_out.get("original_amount"),
                        "debit_account": row_out.get("debit_account"),
                        "credit_account": row_out.get("credit_account"),
                        "suspense_account": src.suspense_account,
                        "suggested_pattern": suggested_pattern,
                        "suggested_rule_yaml": suggested_rule_yaml,
                    })

    staging = pd.DataFrame(staged_rows)
    if not staging.empty:
        staging = staging.sort_values(
            by=["source_name", "source_file", "source_row_number", "entry_id"],
            na_position="last",
            kind="mergesort",
        ).reset_index(drop=True)

    # Row-level validations on staged entries.
    for row in staged_rows:
        src_name = row.get("source_name")
        src_file = row.get("source_file")
        src_row = row.get("source_row_number")

        # COA existence.
        for acct_col in ("debit_account", "credit_account"):
            acct = row.get(acct_col)
            if acct and coa_codes and acct not in coa_codes:
                issues.append(
                    CheckIssue(
                        severity="error",
                        code="unknown_account",
                        message=f"Account not found in chart of accounts: {acct}",
                        source_name=str(src_name) if src_name else None,
                        source_file=str(src_file) if src_file else None,
                        source_row_number=int(src_row) if src_row is not None else None,
                        account=str(acct),
                    )
                )

        # Entry balance check (defensive).
        try:
            amt_str = str(row.get("amount") or "0").strip()
            amt = Decimal(amt_str)
            if amt <= 0:
                raise ValueError("amount missing or non-positive")
        except (InvalidOperation, ValueError):
            issues.append(
                CheckIssue(
                    severity="error",
                    code="bad_amount",
                    message=f"Staged amount is invalid: {row.get('amount')!r}",
                    source_name=str(src_name) if src_name else None,
                    source_file=str(src_file) if src_file else None,
                    source_row_number=int(src_row) if src_row is not None else None,
                    column="amount",
                    raw_value=str(row.get("amount")),
                )
            )

        # Unmapped (landed in suspense) warning.
        if (
            row.get("matched_rule_pattern") in (None, "", "None")
            and row.get("original_description") is not None
        ):
            issues.append(
                CheckIssue(
                    severity=("error" if cfg.strict_unmapped else "warning"),
                    code="unmapped_suspense",
                    message="No mapping rule matched; entry posted to suspense account.",
                    source_name=str(src_name) if src_name else None,
                    source_file=str(src_file) if src_file else None,
                    source_row_number=int(src_row) if src_row is not None else None,
                )
            )

    # Write artifacts.
    staging_cols = [
        "entry_id",
        "date",
        "narration",
        "amount",
        "debit_account",
        "credit_account",
        "source_type",
        "source_name",
        "source_file",
        "source_row_number",
        "matched_rule_pattern",
        "original_description",
        "original_amount",
    ]
    issues_sorted = sorted(issues, key=_issue_sort_key)
    issues_df = pd.DataFrame([i.to_dict() for i in issues_sorted])

    issues_cols = [
        "severity",
        "code",
        "message",
        "source_name",
        "source_file",
        "source_row_number",
        "column",
        "raw_value",
        "account",
    ]
    # When there are no issues, pandas will create an empty DataFrame with no
    # columns. Ensure we still write a stable CSV header for downstream tooling.
    if issues_df.empty and len(issues_df.columns) == 0:
        issues_df = pd.DataFrame(columns=issues_cols)


    # If there are no input files, ``staging`` may be an empty DataFrame with no
    # columns. Ensure we still write a stable CSV header for downstream tooling.
    if staging.empty and len(staging.columns) == 0:
        staging = pd.DataFrame(columns=staging_cols)

    write_csv_df(outdir / "staging.csv", staging, columns=staging_cols)
    write_csv_df(
        outdir / "staging_issues.csv",
        issues_df,
        columns=[
            "severity",
            "code",
            "message",
            "source_name",
            "source_file",
            "source_row_number",
            "column",
            "raw_value",
            "account",
        ],
    )
    unmapped_cols = [
        "entry_id",
        "date",
        "source_name",
        "source_file",
        "source_row_number",
        "original_description",
        "original_amount",
        "debit_account",
        "credit_account",
        "suspense_account",
        "suggested_pattern",
        "suggested_rule_yaml",
    ]
    unmapped_df = pd.DataFrame(unmapped_rows)
    if not unmapped_df.empty:
        unmapped_df = unmapped_df.sort_values(
            by=["source_name", "source_file", "source_row_number", "entry_id"],
            na_position="last",
            kind="mergesort",
        ).reset_index(drop=True)
    if unmapped_df.empty and len(unmapped_df.columns) == 0:
        unmapped_df = pd.DataFrame(columns=unmapped_cols)
    write_csv_df(outdir / "unmapped.csv", unmapped_df, columns=unmapped_cols)
    reclass_df = reclass_template_from_unmapped(unmapped_df)
    write_csv_df(
        outdir / "reclass_template.csv",
        reclass_df,
        columns=RECLASS_TEMPLATE_COLUMNS,
    )



    md = _render_checks_md(
        project_root=project_root,
        cfg=cfg,
        inputs_dir=inputs_dir,
        input_files=sorted(set(input_files)),
        staging=staging,
        issues=issues_sorted,
    )
    write_text(outdir / "checks.md", md)

    return CheckResult(outdir=outdir, staging=staging, issues=issues_sorted)

from __future__ import annotations

import csv
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ledgerloom.core import Entry, Posting
from ledgerloom.engine.money import cents_to_str, str_to_cents

from .models import IngestIssue, IngestResult


_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _slug(s: str) -> str:
    s = s.strip().replace(" ", "_")
    s = _SLUG_RE.sub("_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "source"


def _parse_date(raw: str, *, date_format: str) -> date:
    # We intentionally do NOT guess. Use an explicit format.
    return datetime.strptime(raw.strip(), date_format).date()


def _parse_amount_cents(
    raw: str,
    *,
    thousands_sep: str = ",",
    decimal_sep: str = ".",
) -> int:
    s = raw.strip()
    if not s:
        raise ValueError("empty")

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()

    # Remove common currency symbols and whitespace.
    s = s.replace("$", "").replace("£", "").replace("€", "").replace(" ", "")

    # Normalize separators into Decimal-friendly form.
    if thousands_sep:
        s = s.replace(thousands_sep, "")
    if decimal_sep and decimal_sep != ".":
        s = s.replace(decimal_sep, ".")

    # Allow leading sign
    if s.startswith("-"):
        negative = True
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]

    cents = str_to_cents(s)
    return -cents if negative else cents


def ingest_journal_entries_csv(
    path: Path,
    *,
    source_name: str = "Journal Entries",
    strict: bool = True,
    date_format: str = "%Y-%m-%d",
    thousands_sep: str = ",",
    decimal_sep: str = ".",
    entry_id_col: str = "entry_id",
    date_col: str = "date",
    narration_col: str = "narration",
    account_col: str = "account",
    debit_col: str = "debit",
    credit_col: str = "credit",
) -> IngestResult:
    """Ingest a posting-line journal CSV into balanced Entries.

    Expected columns (default names):
      entry_id,date,narration,account,debit,credit

    Notes
    -----
    - Row numbers are 1-based relative to the first data row.
    - Dates are parsed with an explicit strptime format (no guessing).
    - Exactly one of debit/credit must be non-zero per row.
    - Rows are grouped by entry_id and validated as balanced entries.
    """

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    required = (entry_id_col, date_col, narration_col, account_col, debit_col, credit_col)
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Journal entries source requires columns {missing_cols} but file has {list(df.columns)}"
        )

    issues: list[IngestIssue] = []
    entries: list[Entry] = []

    src_slug = _slug(source_name)
    filename = path.name

    # Preserve entry ordering as first-seen in the file.
    buckets: dict[str, dict[str, object]] = {}
    invalid_entry_ids: set[str] = set()

    def _issue(
        *,
        row_number: int,
        code: str,
        message: str,
        column: str | None = None,
        raw_value: str | None = None,
        entry_id: str | None = None,
    ) -> None:
        issues.append(
            IngestIssue(
                row_number=row_number,
                code=code,
                message=message,
                column=column,
                raw_value=raw_value,
            )
        )
        if entry_id:
            invalid_entry_ids.add(entry_id)
        if strict:
            raise ValueError(f"Row {row_number}: {code}: {message}")

    for i, rec in enumerate(df.to_dict(orient="records"), start=1):
        raw_entry_id = str(rec.get(entry_id_col, "")).strip()
        raw_date = str(rec.get(date_col, "")).strip()
        raw_narr = str(rec.get(narration_col, "")).strip()
        raw_acct = str(rec.get(account_col, "")).strip()
        raw_debit = str(rec.get(debit_col, "")).strip()
        raw_credit = str(rec.get(credit_col, "")).strip()

        if not raw_entry_id:
            _issue(
                row_number=i,
                code="missing_entry_id",
                message="Missing entry_id",
                column=entry_id_col,
                raw_value=str(rec.get(entry_id_col, "")),
            )
            continue

        if not raw_date:
            _issue(
                row_number=i,
                code="missing_date",
                message="Missing date",
                column=date_col,
                raw_value=str(rec.get(date_col, "")),
                entry_id=raw_entry_id,
            )
            continue

        try:
            dt = _parse_date(raw_date, date_format=date_format)
        except Exception as e:
            _issue(
                row_number=i,
                code="parse_date",
                message=f"Could not parse date with format '{date_format}': {e}",
                column=date_col,
                raw_value=raw_date,
                entry_id=raw_entry_id,
            )
            continue

        if not raw_acct:
            _issue(
                row_number=i,
                code="missing_account",
                message="Missing account",
                column=account_col,
                raw_value=str(rec.get(account_col, "")),
                entry_id=raw_entry_id,
            )
            continue

        debit_cents = 0
        credit_cents = 0

        if raw_debit:
            try:
                debit_cents = _parse_amount_cents(
                    raw_debit, thousands_sep=thousands_sep, decimal_sep=decimal_sep
                )
            except Exception as e:
                _issue(
                    row_number=i,
                    code="parse_debit",
                    message=f"Could not parse debit: {e}",
                    column=debit_col,
                    raw_value=raw_debit,
                    entry_id=raw_entry_id,
                )
                continue

        if raw_credit:
            try:
                credit_cents = _parse_amount_cents(
                    raw_credit, thousands_sep=thousands_sep, decimal_sep=decimal_sep
                )
            except Exception as e:
                _issue(
                    row_number=i,
                    code="parse_credit",
                    message=f"Could not parse credit: {e}",
                    column=credit_col,
                    raw_value=raw_credit,
                    entry_id=raw_entry_id,
                )
                continue

        if debit_cents < 0 or credit_cents < 0:
            _issue(
                row_number=i,
                code="negative_amount",
                message=(
                    "Debit/credit amounts must be positive (use debit vs credit columns, "
                    "not negative signs)."
                ),
                entry_id=raw_entry_id,
            )
            continue

        if debit_cents > 0 and credit_cents > 0:
            _issue(
                row_number=i,
                code="both_debit_credit",
                message="Row has both debit and credit; exactly one must be non-zero.",
                entry_id=raw_entry_id,
            )
            continue

        if debit_cents == 0 and credit_cents == 0:
            _issue(
                row_number=i,
                code="zero_amount_line",
                message="Row has neither debit nor credit (both zero/blank).",
                entry_id=raw_entry_id,
            )
            continue

        narration = raw_narr or "(no narration)"

        b = buckets.get(raw_entry_id)
        if b is None:
            buckets[raw_entry_id] = {
                "dt": dt,
                "narration": narration,
                "postings": [],
                "row_numbers": [i],
            }
        else:
            # Enforce consistency within an entry_id.
            if b["dt"] != dt:
                _issue(
                    row_number=i,
                    code="inconsistent_date",
                    message=(
                        f"Entry '{raw_entry_id}' has inconsistent dates within the same entry_id."
                    ),
                    entry_id=raw_entry_id,
                )
                continue
            if b["narration"] != narration:
                _issue(
                    row_number=i,
                    code="inconsistent_narration",
                    message=(
                        f"Entry '{raw_entry_id}' has inconsistent narration within the same entry_id."
                    ),
                    entry_id=raw_entry_id,
                )
                continue
            b["row_numbers"].append(i)

        amt_cents = debit_cents if debit_cents > 0 else credit_cents
        amt = Decimal(cents_to_str(abs(amt_cents)))

        posting = (
            Posting(account=raw_acct, debit=amt)
            if debit_cents > 0
            else Posting(account=raw_acct, credit=amt)
        )
        buckets[raw_entry_id]["postings"].append(posting)

    # Build Entries in first-seen order (dict preserves insertion order).
    for entry_id, b in buckets.items():
        if entry_id in invalid_entry_ids:
            continue

        dt = b["dt"]
        narration = b["narration"]
        postings = b["postings"]
        row_numbers = b["row_numbers"]

        meta = {
            "entry_id": f"journal:{src_slug}:{filename}:{entry_id}",
            "source_type": "journal_entries.v1",
            "source_name": source_name,
            "source_file": filename,
            "row_numbers": ",".join(str(n) for n in row_numbers),
        }

        entry = Entry(dt=dt, narration=narration, postings=postings, meta=meta)
        try:
            entry.validate_balanced()
        except Exception as e:
            issues.append(
                IngestIssue(
                    row_number=int(row_numbers[0]),
                    code="unbalanced_entry",
                    message=f"Entry '{entry_id}' is unbalanced: {e}",
                )
            )
            if strict:
                raise
            continue

        entries.append(entry)

    return IngestResult(entries=entries, issues=issues)



def staging_postings_from_journal_entries_csv(
    path: Path,
    *,
    source_name: str,
    source_path: str,
    entry_kind: str = "adjustment",
    date_format: str = "%Y-%m-%d",
    thousands_sep: str = ",",
    decimal_sep: str = ".",
    entry_id_col: str = "entry_id",
    date_col: str = "date",
    narration_col: str = "narration",
    account_col: str = "account",
    debit_col: str = "debit",
    credit_col: str = "credit",
) -> tuple[list[dict[str, object]], list[IngestIssue]]:
    """Parse a journal_entries.v1 CSV into staging_postings rows.

    This is a lightweight helper for `ledgerloom check`: it does **not** build
    `Entry` objects or validate that each entry balances. Instead it normalizes
    each input posting-line into the canonical staging schema:

      - one staging row per CSV row
      - `debit` is positive
      - `credit` is negative (to match postings/trial-balance sign conventions)
      - `source_row_number` is 1-based over *data rows* (header excluded)
    """

    issues: list[IngestIssue] = []
    # Values are mostly strings, but `source_row_number` is an int.
    rows: list[dict[str, object]] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        required_cols = {entry_id_col, date_col, account_col, debit_col, credit_col}
        missing = sorted(c for c in required_cols if c not in fieldnames)
        if missing:
            issues.append(
                IngestIssue(
                    row_number=None,
                    code="missing_columns",
                    message=f"Missing required column(s): {', '.join(missing)}",
                )
            )
            return rows, issues

        has_narration = narration_col in fieldnames

        for row_number, row in enumerate(reader, start=1):
            # Required strings.
            entry_id = (row.get(entry_id_col) or "").strip()
            if not entry_id:
                issues.append(
                    IngestIssue(
                        row_number=row_number,
                        code="missing_entry_id",
                        message="entry_id is required",
                        column=entry_id_col,
                        raw_value=row.get(entry_id_col),
                    )
                )
                continue

            raw_date = (row.get(date_col) or "").strip()
            if not raw_date:
                issues.append(
                    IngestIssue(
                        row_number=row_number,
                        code="missing_date",
                        message="date is required",
                        column=date_col,
                        raw_value=row.get(date_col),
                    )
                )
                continue

            account = (row.get(account_col) or "").strip()
            if not account:
                issues.append(
                    IngestIssue(
                        row_number=row_number,
                        code="missing_account",
                        message="account is required",
                        column=account_col,
                        raw_value=row.get(account_col),
                    )
                )
                continue

            # Normalize/validate date.
            try:
                dt = _parse_date(raw_date, date_format=date_format)
            except ValueError as e:
                issues.append(
                    IngestIssue(
                        row_number=row_number,
                        code="invalid_date",
                        message=str(e),
                        column=date_col,
                        raw_value=raw_date,
                    )
                )
                continue

            raw_debit = (row.get(debit_col) or "").strip()
            raw_credit = (row.get(credit_col) or "").strip()

            try:
                debit_cents = _parse_amount_cents(
                    raw_debit, thousands_sep=thousands_sep, decimal_sep=decimal_sep
                ) if raw_debit else 0
                credit_cents = _parse_amount_cents(
                    raw_credit, thousands_sep=thousands_sep, decimal_sep=decimal_sep
                ) if raw_credit else 0
            except ValueError as e:
                # Prefer pointing at the provided column.
                bad_col = debit_col if raw_debit else credit_col
                bad_val = raw_debit if raw_debit else raw_credit
                issues.append(
                    IngestIssue(
                        row_number=row_number,
                        code="invalid_amount",
                        message=str(e),
                        column=bad_col,
                        raw_value=bad_val,
                    )
                )
                continue

            # Must provide exactly one of debit/credit (non-zero after parse).
            if (debit_cents != 0) == (credit_cents != 0):
                issues.append(
                    IngestIssue(
                        row_number=row_number,
                        code="invalid_debit_credit",
                        message="Exactly one of debit or credit must be provided",
                    )
                )
                continue

            # Staging convention: debit positive, credit negative.
            debit_out = ""
            credit_out = ""
            if debit_cents != 0:
                debit_out = cents_to_str(abs(debit_cents))
            else:
                credit_out = cents_to_str(-abs(credit_cents))

            narration = (row.get(narration_col) or "").strip() if has_narration else ""

            # Keep the staging schema consistent across adapters:
            # `source_row_number` is an int (1-based, header excluded).
            rows.append(
                {
                    "source_name": source_name,
                    "source_path": source_path,
                    "source_row_number": row_number,
                    "entry_id": entry_id,
                    "date": dt.isoformat(),
                    "narration": narration,
                    "account": account,
                    "debit": debit_out,
                    "credit": credit_out,
                    "entry_kind": entry_kind,
                }
            )

    return rows, issues

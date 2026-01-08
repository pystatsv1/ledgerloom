from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from collections.abc import Iterable

from ledgerloom.core import Entry, Posting
from ledgerloom.engine.money import cents_to_str, str_to_cents

from ledgerloom.project.config import BankFeedSource as ProjectBankFeedSource

from .models import BankFeedSourceConfig, IngestIssue


@dataclass(frozen=True)
class IngestResult:
    """Result of ingesting a single input file."""

    entries: list[Entry]
    issues: list[IngestIssue]


_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _slug(s: str) -> str:
    s = s.strip().replace(" ", "_")
    s = _SLUG_RE.sub("_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "source"


def _parse_date(raw: str, *, date_format: str) -> date:
    # We intentionally do NOT guess. Config must provide a strptime format.
    return datetime.strptime(raw.strip(), date_format).date()


def _parse_amount_cents(
    raw: str,
    *,
    thousands_sep: str,
    decimal_sep: str,
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


def _compile_rules(rules: Iterable[tuple[str, str | None]]) -> list[tuple[re.Pattern[str], str | None]]:
    compiled: list[tuple[re.Pattern[str], str | None]] = []
    for pat, narration in rules:
        compiled.append((re.compile(pat, flags=re.IGNORECASE), narration))
    return compiled


def ingest_bank_feed_csv(
    path: Path,
    source: BankFeedSourceConfig | ProjectBankFeedSource,
    *,
    strict: bool = True,
) -> IngestResult:
    """Ingest a bank feed CSV into Entries.

    Notes
    -----
    - Row numbers are 1-based relative to the first data row.
    - Dates are parsed with ``source.date_format`` (no guessing).
    - Amount parsing uses configured thousands/decimal separators.
    """

    # Convert YAML-facing Project config sources into ingest config.
    if isinstance(source, ProjectBankFeedSource):
        source = BankFeedSourceConfig.from_project_source(source)

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    missing_cols = [
        c
        for c in (source.date_col, source.description_col, source.amount_col)
        if c not in df.columns
    ]
    if missing_cols:
        raise ValueError(
            f"Source '{source.name}' requires columns {missing_cols} but file has {list(df.columns)}"
        )

    # Pre-compile rules once. Invalid regex should fail fast.
    compiled_rules = _compile_rules([(r.pattern, r.narration) for r in source.rules])

    entries: list[Entry] = []
    issues: list[IngestIssue] = []

    src_slug = _slug(source.name)
    filename = path.name

    for i, rec in enumerate(df.to_dict(orient="records"), start=1):
        raw_date = str(rec.get(source.date_col, ""))
        raw_desc = str(rec.get(source.description_col, ""))
        raw_amt = str(rec.get(source.amount_col, ""))

        entry_id = f"bank:{src_slug}:{filename}:{i}"

        if not raw_date.strip():
            issues.append(
                IngestIssue(
                    row_number=i,
                    code="missing_date",
                    message="Missing date",
                    column=source.date_col,
                    raw_value=raw_date,
                )
            )
            if strict:
                raise ValueError(f"Row {i}: missing date")
            continue

        try:
            dt = _parse_date(raw_date, date_format=source.date_format)
        except Exception as e:
            issues.append(
                IngestIssue(
                    row_number=i,
                    code="parse_date",
                    message=f"Could not parse date with format '{source.date_format}': {e}",
                    column=source.date_col,
                    raw_value=raw_date,
                )
            )
            if strict:
                raise ValueError(f"Row {i}: bad date '{raw_date}'") from e
            continue

        if not raw_amt.strip():
            issues.append(
                IngestIssue(
                    row_number=i,
                    code="missing_amount",
                    message="Missing amount",
                    column=source.amount_col,
                    raw_value=raw_amt,
                )
            )
            if strict:
                raise ValueError(f"Row {i}: missing amount")
            continue

        try:
            cents = _parse_amount_cents(
                raw_amt,
                thousands_sep=source.amount_thousands_sep,
                decimal_sep=source.amount_decimal_sep,
            )
        except Exception as e:
            issues.append(
                IngestIssue(
                    row_number=i,
                    code="parse_amount",
                    message=f"Could not parse amount: {e}",
                    column=source.amount_col,
                    raw_value=raw_amt,
                )
            )
            if strict:
                raise ValueError(f"Row {i}: bad amount '{raw_amt}'") from e
            continue

        if source.invert_amount_sign:
            cents = -cents

        if cents == 0:
            issues.append(
                IngestIssue(
                    row_number=i,
                    code="zero_amount",
                    message="Zero-amount row (skipped)",
                    column=source.amount_col,
                    raw_value=raw_amt,
                )
            )
            if strict:
                raise ValueError(f"Row {i}: zero amount")
            continue

        desc = raw_desc.strip()

        # Apply rules.
        target_account = source.suspense_account
        narration = desc or "(no description)"
        matched_pattern: str | None = None
        for (regex, narration_override), rule in zip(compiled_rules, source.rules, strict=True):
            if regex.search(desc):
                target_account = rule.account
                narration = rule.narration or narration
                matched_pattern = rule.pattern
                break

        is_outflow = cents < 0
        abs_cents = abs(cents)
        amt = Decimal(cents_to_str(abs_cents))

        if is_outflow:
            postings = [
                Posting(account=source.default_account, credit=amt),
                Posting(account=target_account, debit=amt),
            ]
        else:
            postings = [
                Posting(account=source.default_account, debit=amt),
                Posting(account=target_account, credit=amt),
            ]

        meta = {
            "entry_id": entry_id,
            "source_type": source.source_type,
            "source_name": source.name,
            "source_file": filename,
            "row_number": i,
            "original_description": desc,
            "original_amount": raw_amt,
            "matched_rule_pattern": matched_pattern,
        }

        entries.append(Entry(dt=dt, narration=narration, postings=postings, meta=meta))

    return IngestResult(entries=entries, issues=issues)

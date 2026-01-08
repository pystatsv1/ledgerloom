from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from ledgerloom.project.config import BankFeedSource


@dataclass(frozen=True)
class BankFeedRule:
    """A single categorization rule for bank feeds.

    Rules are applied in order; the first regex pattern match wins.
    """

    pattern: str
    account: str
    narration: str | None = None

    @classmethod
    def from_rule_mapping(cls, spec: Any) -> BankFeedRule:
        """Coerce a rule spec into a normalized :class:`BankFeedRule`.

        ``ProjectConfig`` parses YAML rules into ``ledgerloom.project.config.BankFeedRule``
        objects. For backward compatibility (and convenience in tests), we also
        accept mapping-shaped rule specs.
        """

        if isinstance(spec, cls):
            return spec

        if isinstance(spec, Mapping):
            pattern = str(spec.get("pattern", "")).strip()
            account = str(spec.get("account", "")).strip()
            narration_raw = spec.get("narration")
        else:
            # Accept objects with the expected attributes (e.g. project.config.BankFeedRule).
            pattern = str(getattr(spec, "pattern", "")).strip()
            account = str(getattr(spec, "account", "")).strip()
            narration_raw = getattr(spec, "narration", None)
        narration = None if narration_raw is None else str(narration_raw)
        if not pattern:
            raise ValueError("Bank feed rule missing required 'pattern'.")
        if not account:
            raise ValueError("Bank feed rule missing required 'account'.")
        return cls(pattern=pattern, account=account, narration=narration)


@dataclass(frozen=True)
class BankFeedSourceConfig:
    """Normalized configuration for the bank-feed CSV adapter."""

    source_type: Literal["bank_feed.v1"]
    name: str
    default_account: str
    date_format: str

    # CSV column names
    date_col: str
    description_col: str
    amount_col: str

    invert_amount_sign: bool = False
    suspense_account: str = "Expenses:Uncategorized"
    amount_thousands_sep: str = ","
    amount_decimal_sep: str = "."

    rules: tuple[BankFeedRule, ...] = ()

    @classmethod
    def from_project_source(cls, src: BankFeedSource) -> BankFeedSourceConfig:
        return cls(
            source_type="bank_feed.v1",
            name=src.name,
            default_account=src.default_account,
            date_format=src.date_format,
            date_col=src.columns.date,
            description_col=src.columns.description,
            amount_col=src.columns.amount,
            invert_amount_sign=src.invert_amount_sign,
            suspense_account=src.suspense_account,
            amount_thousands_sep=src.amount_thousands_sep,
            amount_decimal_sep=src.amount_decimal_sep,
            rules=tuple(BankFeedRule.from_rule_mapping(r) for r in src.rules),
        )


@dataclass(frozen=True)
class IngestIssue:
    """A row-level ingestion issue.

    In PR04 we will surface these issues in ``ledgerloom check``.
    """

    row_number: int
    code: str
    message: str
    column: str | None = None
    raw_value: str | None = None

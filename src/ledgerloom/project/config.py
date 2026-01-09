"""LedgerLoom project configuration.

This module introduces a *versioned* project configuration document.

Why versioning matters
----------------------
LedgerLoom is both a teaching tool *and* (increasingly) a practical tool.
The config schema is part of the public contract: once a user has a
``ledgerloom.yaml`` on disk, we must be able to keep reading it.

For v0.2.x, we keep this deliberately small and focused:

* Project metadata (name/period/currency)
* Location of the chart of accounts file
* A list of data sources (bank-feed v1 only, for now)
* Output root

Later PRs will expand the ingestion and CLI workflows around this config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml


SCHEMA_ID_PROJECT_CONFIG_V1 = "ledgerloom.project_config.v1"

# Source types are part of the public UX (accountants edit these), so keep them
# short and descriptive.
SOURCE_TYPE_BANK_FEED_V1 = "bank_feed.v1"


def _require_str(d: Mapping[str, Any], key: str) -> str:
    val = d.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"Expected non-empty string for '{key}'")
    return val


def _require_bool(d: Mapping[str, Any], key: str, *, default: bool = False) -> bool:
    if key not in d:
        return default
    val = d[key]
    if not isinstance(val, bool):
        raise ValueError(f"Expected boolean for '{key}'")
    return val


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    name: str
    period: str
    currency: str = "USD"

    @staticmethod
    def from_mapping(d: Mapping[str, Any]) -> "ProjectInfo":
        name = _require_str(d, "name")
        period = _require_str(d, "period")
        currency = d.get("currency", "USD")
        if not isinstance(currency, str) or not currency.strip():
            raise ValueError("Expected non-empty string for 'currency'")
        return ProjectInfo(name=name.strip(), period=period.strip(), currency=currency.strip())

    def to_dict(self) -> dict[str, Any]:
        # Deterministic key order.
        return {
            "name": self.name,
            "period": self.period,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class BankFeedColumns:
    date: str
    description: str
    amount: str
    tx_type: str | None = None

    @staticmethod
    def from_mapping(d: Mapping[str, Any]) -> "BankFeedColumns":
        date = _require_str(d, "date")
        description = _require_str(d, "description")
        amount = _require_str(d, "amount")
        tx_type = d.get("type")
        if tx_type is not None and (not isinstance(tx_type, str) or not tx_type.strip()):
            raise ValueError("Expected string for 'type' if provided")
        return BankFeedColumns(date=date, description=description, amount=amount, tx_type=tx_type)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "date": self.date,
            "description": self.description,
            "amount": self.amount,
        }
        if self.tx_type is not None:
            out["type"] = self.tx_type
        return out


@dataclass(frozen=True, slots=True)
class BankFeedRule:
    pattern: str
    account: str
    narration: str | None = None

    @staticmethod
    def from_mapping(d: Mapping[str, Any]) -> "BankFeedRule":
        pattern = _require_str(d, "pattern")
        account = _require_str(d, "account")
        narration = d.get("narration")
        if narration is not None and (not isinstance(narration, str) or not narration.strip()):
            raise ValueError("Expected string for 'narration' if provided")
        return BankFeedRule(pattern=pattern, account=account, narration=narration)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "pattern": self.pattern,
            "account": self.account,
        }
        if self.narration is not None:
            out["narration"] = self.narration
        return out


@dataclass(frozen=True, slots=True)
class BankFeedSource:
    """A "bank feed" CSV source.

    This is intentionally small. v1 assumes:
    - each row becomes a 2-leg entry (default_account <-> mapped account)
    - mapping uses regex rules on the description
    """

    name: str
    file_pattern: str
    default_account: str
    columns: BankFeedColumns

    # IMPORTANT: Banks use many date formats. Require an explicit format
    # string so ingestion does not "guess" and silently swap day/month.
    # Example: "%m/%d/%Y".
    date_format: str

    # Amount parsing is locale-sensitive. Configure separators explicitly.
    # US example: thousands="," decimal="."
    # EU example: thousands="." decimal=",".
    amount_thousands_sep: str = ","
    amount_decimal_sep: str = "."

    source_type: str = field(default=SOURCE_TYPE_BANK_FEED_V1, init=False)
    invert_amount_sign: bool = False
    suspense_account: str = "Expenses:Uncategorized"
    rules: list[BankFeedRule] = field(default_factory=list)

    @staticmethod
    def from_mapping(d: Mapping[str, Any]) -> "BankFeedSource":
        source_type = d.get("source_type", SOURCE_TYPE_BANK_FEED_V1)
        if source_type != SOURCE_TYPE_BANK_FEED_V1:
            raise ValueError(
                f"Unsupported source_type '{source_type}'. Expected '{SOURCE_TYPE_BANK_FEED_V1}'."
            )

        name = _require_str(d, "name")
        file_pattern = _require_str(d, "file_pattern")
        default_account = _require_str(d, "default_account")
        date_format = _require_str(d, "date_format")

        amount_thousands_sep = d.get("amount_thousands_sep", ",")
        if not isinstance(amount_thousands_sep, str):
            raise ValueError("Expected string for 'amount_thousands_sep'")
        amount_decimal_sep = d.get("amount_decimal_sep", ".")
        if not isinstance(amount_decimal_sep, str) or not amount_decimal_sep.strip():
            raise ValueError("Expected non-empty string for 'amount_decimal_sep'")

        suspense_account = d.get("suspense_account", "Expenses:Uncategorized")
        if not isinstance(suspense_account, str) or not suspense_account.strip():
            raise ValueError("Expected non-empty string for 'suspense_account'")
        invert_amount_sign = _require_bool(d, "invert_amount_sign", default=False)

        cols_raw = d.get("columns")
        if not isinstance(cols_raw, Mapping):
            raise ValueError("Expected mapping for 'columns'")
        columns = BankFeedColumns.from_mapping(cols_raw)

        rules_raw = d.get("rules", [])
        if not isinstance(rules_raw, list):
            raise ValueError("Expected list for 'rules'")
        rules: list[BankFeedRule] = []
        for i, rr in enumerate(rules_raw):
            if not isinstance(rr, Mapping):
                raise ValueError(f"Expected mapping for rules[{i}]")
            rules.append(BankFeedRule.from_mapping(rr))

        return BankFeedSource(
            name=name,
            file_pattern=file_pattern,
            default_account=default_account,
            columns=columns,
            date_format=date_format,
            amount_thousands_sep=amount_thousands_sep,
            amount_decimal_sep=amount_decimal_sep,
            invert_amount_sign=invert_amount_sign,
            suspense_account=suspense_account,
            rules=rules,
        )

    def to_dict(self) -> dict[str, Any]:
        # Deterministic key order.
        return {
            "source_type": self.source_type,
            "name": self.name,
            "file_pattern": self.file_pattern,
            "default_account": self.default_account,
            "columns": self.columns.to_dict(),
            "date_format": self.date_format,
            "amount_thousands_sep": self.amount_thousands_sep,
            "amount_decimal_sep": self.amount_decimal_sep,
            "invert_amount_sign": self.invert_amount_sign,
            "suspense_account": self.suspense_account,
            "rules": [r.to_dict() for r in self.rules],
        }


@dataclass(frozen=True, slots=True)
class OutputsConfig:
    root: str = "outputs"

    @staticmethod
    def from_mapping(d: Mapping[str, Any]) -> "OutputsConfig":
        root = d.get("root", "outputs")
        if not isinstance(root, str) or not root.strip():
            raise ValueError("Expected non-empty string for outputs.root")
        return OutputsConfig(root=root.strip())

    def to_dict(self) -> dict[str, Any]:
        return {"root": self.root}


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Top-level project config document (v1)."""

    project: ProjectInfo
    chart_of_accounts: str
    strict_unmapped: bool = False
    sources: list[BankFeedSource] = field(default_factory=list)
    outputs: OutputsConfig = field(default_factory=OutputsConfig)
    schema_id: str = SCHEMA_ID_PROJECT_CONFIG_V1

    @staticmethod
    def from_mapping(d: Mapping[str, Any]) -> "ProjectConfig":
        schema_id = d.get("schema_id", SCHEMA_ID_PROJECT_CONFIG_V1)
        if schema_id != SCHEMA_ID_PROJECT_CONFIG_V1:
            raise ValueError(
                f"Unsupported project config schema_id '{schema_id}'. Expected '{SCHEMA_ID_PROJECT_CONFIG_V1}'."
            )

        proj_raw = d.get("project")
        if not isinstance(proj_raw, Mapping):
            raise ValueError("Expected mapping for 'project'")
        project = ProjectInfo.from_mapping(proj_raw)

        chart_of_accounts = _require_str(d, "chart_of_accounts")


        strict_unmapped_raw = d.get("strict_unmapped", False)
        if not isinstance(strict_unmapped_raw, bool):
            raise ValueError("Expected boolean for 'strict_unmapped'")
        strict_unmapped = strict_unmapped_raw

        sources_raw = d.get("sources", [])
        if not isinstance(sources_raw, list):
            raise ValueError("Expected list for 'sources'")
        sources: list[BankFeedSource] = []
        for i, s in enumerate(sources_raw):
            if not isinstance(s, Mapping):
                raise ValueError(f"Expected mapping for sources[{i}]")
            sources.append(BankFeedSource.from_mapping(s))

        outputs_raw = d.get("outputs", {})
        if not isinstance(outputs_raw, Mapping):
            raise ValueError("Expected mapping for 'outputs'")
        outputs = OutputsConfig.from_mapping(outputs_raw)

        return ProjectConfig(
            schema_id=schema_id,
            project=project,
            chart_of_accounts=chart_of_accounts,
            strict_unmapped=strict_unmapped,
            sources=sources,
            outputs=outputs,
        )

    @classmethod
    def load_yaml(cls, path: Path) -> "ProjectConfig":
        """Load and validate a project config YAML file."""

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("Expected YAML document to be a mapping")
        return cls.from_mapping(raw)

    def to_dict(self) -> dict[str, Any]:
        """Return a normalized mapping with deterministic key ordering."""

        return {
            "schema_id": self.schema_id,
            "project": self.project.to_dict(),
            "chart_of_accounts": self.chart_of_accounts,
            "strict_unmapped": self.strict_unmapped,
            "sources": [s.to_dict() for s in self.sources],
            "outputs": self.outputs.to_dict(),
        }

    def dump_yaml(self, path: Path) -> None:
        """Write a normalized YAML config (LF newlines, stable key order)."""

        text = yaml.safe_dump(self.to_dict(), sort_keys=False)
        # Ensure LF newlines regardless of platform.
        path.write_text(text, encoding="utf-8", newline="\n")

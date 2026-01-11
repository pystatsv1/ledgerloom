from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from ledgerloom.project.config import ProjectConfig


def test_project_config_yaml_roundtrip_is_deterministic(tmp_path: Path) -> None:
    cfg_yaml = """
schema_id: ledgerloom.project_config.v1
outputs:
  root: outputs
chart_of_accounts: config/chart_of_accounts.yaml
project:
  currency: USD
  name: Acme Corp
  period: 2026-01
sources:
  - source_type: bank_feed.v1
    name: Chase Checking
    file_pattern: inputs/2026-01/chase_*.csv
    default_account: Assets:US:Chase:Checking
    date_format: "%m/%d/%Y"
    columns:
      description: Description
      amount: Amount
      date: Posting Date
    amount_thousands_sep: ","
    amount_decimal_sep: "."
    invert_amount_sign: true
    suspense_account: Expenses:Uncategorized
    rules:
      - pattern: Starbucks|Peets
        account: Expenses:Meals
        narration: Coffee
""".lstrip()

    path = tmp_path / "ledgerloom.yaml"
    path.write_text(cfg_yaml, encoding="utf-8", newline="\n")

    cfg = ProjectConfig.load_yaml(path)

    expected = {
        "schema_id": "ledgerloom.project_config.v1",
        "project": {"name": "Acme Corp", "period": "2026-01", "currency": "USD"},
        "chart_of_accounts": "config/chart_of_accounts.yaml",
        "strict_unmapped": False,
        "sources": [
            {
                "source_type": "bank_feed.v1",
                "name": "Chase Checking",
                "file_pattern": "inputs/2026-01/chase_*.csv",
                "default_account": "Assets:US:Chase:Checking",
                "date_format": "%m/%d/%Y",
                "columns": {
                    "date": "Posting Date",
                    "description": "Description",
                    "amount": "Amount",
                },
                "amount_thousands_sep": ",",
                "amount_decimal_sep": ".",
                "invert_amount_sign": True,
                "suspense_account": "Expenses:Uncategorized",
                "rules": [
                    {
                        "pattern": "Starbucks|Peets",
                        "account": "Expenses:Meals",
                        "narration": "Coffee",
                    }
                ],
            }
        ],
        "outputs": {"root": "outputs"},
    }

    assert cfg.to_dict() == expected

    # Re-dump + re-load to ensure stable representation.
    dumped = tmp_path / "dumped.yaml"
    cfg.dump_yaml(dumped)
    cfg2 = ProjectConfig.load_yaml(dumped)
    assert cfg2.to_dict() == expected


def test_project_config_yaml_roundtrip_is_deterministic_v2(tmp_path: Path) -> None:
    cfg_yaml = """
schema_id: ledgerloom.project_config.v2
outputs:
  root: outputs
chart_of_accounts: config/chart_of_accounts.yaml
project:
  currency: USD
  name: Acme Corp
  period: 2026-01
sources:
  - source_type: bank_feed.v1
    name: Chase Checking
    file_pattern: inputs/2026-01/chase_*.csv
    default_account: Assets:US:Chase:Checking
    date_format: "%m/%d/%Y"
    columns:
      description: Description
      amount: Amount
      date: Posting Date
    amount_thousands_sep: ","
    amount_decimal_sep: "."
    invert_amount_sign: true
    suspense_account: Expenses:Uncategorized
    rules:
      - pattern: Starbucks|Peets
        account: Expenses:Meals
        narration: Coffee
  - source_type: journal_entries.v1
    name: Adjustments
    file_pattern: inputs/{period}/adjustments.csv
    entry_kind: adjustment
    columns:
      entry_id: entry_id
      date: date
      narration: narration
      account: account
      debit: debit
      credit: credit
    date_format: "%Y-%m-%d"
    amount_thousands_sep: ","
    amount_decimal_sep: "."
""".lstrip()

    path = tmp_path / "ledgerloom.yaml"
    path.write_text(cfg_yaml, encoding="utf-8", newline="\n")

    cfg = ProjectConfig.load_yaml(path)

    expected = {
        "schema_id": "ledgerloom.project_config.v2",
        "project": {"name": "Acme Corp", "period": "2026-01", "currency": "USD"},
        "chart_of_accounts": "config/chart_of_accounts.yaml",
        "strict_unmapped": False,
        "sources": [
            {
                "source_type": "bank_feed.v1",
                "name": "Chase Checking",
                "file_pattern": "inputs/2026-01/chase_*.csv",
                "default_account": "Assets:US:Chase:Checking",
                "date_format": "%m/%d/%Y",
                "columns": {
                    "date": "Posting Date",
                    "description": "Description",
                    "amount": "Amount",
                },
                "amount_thousands_sep": ",",
                "amount_decimal_sep": ".",
                "invert_amount_sign": True,
                "suspense_account": "Expenses:Uncategorized",
                "rules": [
                    {
                        "pattern": "Starbucks|Peets",
                        "account": "Expenses:Meals",
                        "narration": "Coffee",
                    }
                ],
            },
            {
                "source_type": "journal_entries.v1",
                "name": "Adjustments",
                "file_pattern": "inputs/{period}/adjustments.csv",
                "entry_kind": "adjustment",
                "columns": {
                    "entry_id": "entry_id",
                    "date": "date",
                    "narration": "narration",
                    "account": "account",
                    "debit": "debit",
                    "credit": "credit",
                },
                "date_format": "%Y-%m-%d",
                "amount_thousands_sep": ",",
                "amount_decimal_sep": ".",
            },
        ],
        "outputs": {"root": "outputs"},
    }

    assert cfg.to_dict() == expected

    dumped = tmp_path / "dumped.yaml"
    cfg.dump_yaml(dumped)
    cfg2 = ProjectConfig.load_yaml(dumped)
    assert cfg2.to_dict() == expected

def test_project_config_v1_rejects_journal_entries_sources(tmp_path: Path) -> None:
    cfg_yaml = textwrap.dedent("""
    schema_id: ledgerloom.project_config.v1
    project:
      name: Acme Corp
      period: 2026-01
      currency: USD
    chart_of_accounts: config/chart_of_accounts.yaml
    outputs:
      root: outputs
    sources:
      - source_type: journal_entries.v1
        name: Adjustments
        file_pattern: inputs/{period}/adjustments.csv
        entry_kind: adjustment
    """).lstrip()

    path = tmp_path / "ledgerloom.yaml"
    path.write_text(cfg_yaml, encoding="utf-8", newline="\n")

    with pytest.raises(
        ValueError,
        match=r"ledgerloom\.project_config\.v1 supports only bank_feed\.v1 sources",
    ):
        ProjectConfig.load_yaml(path)


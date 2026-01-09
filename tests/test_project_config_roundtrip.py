from __future__ import annotations

from pathlib import Path

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

from __future__ import annotations

from pathlib import Path

from ledgerloom.project.coa import load_chart_of_accounts, missing_account_codes, validate_coa


def test_load_and_validate_coa_v1(tmp_path: Path) -> None:
    coa_path = tmp_path / "chart_of_accounts.yaml"
    coa_path.write_text(
        """
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Cash
    name: Cash
    account_type: ASSET

  - code: Assets:AccumDepr
    name: Accumulated depreciation
    account_type: ASSET
    is_contra: true
    rollup_code: Assets:FixedAssets

  - code: Assets:FixedAssets
    name: Fixed assets
    account_type: ASSET

  - code: Revenue:Sales
    name: Sales revenue
    account_type: REVENUE

  - code: Expenses:Meals
    name: Meals
    account_type: EXPENSE
""".lstrip(),
        encoding="utf-8",
    )

    result = load_chart_of_accounts(coa_path)
    assert result.schema_id == "ledgerloom.chart_of_accounts.v1"
    assert len(result.accounts) == 5

    messages = validate_coa(result.accounts)
    # The engine validator returns a list of PASS/FAIL strings.
    assert messages, "expected at least one COA validation message"
    assert any(m.startswith("PASS") for m in messages)
    assert not any(m.startswith("FAIL") for m in messages)


def test_missing_account_codes(tmp_path: Path) -> None:
    coa_path = tmp_path / "chart_of_accounts.yaml"
    coa_path.write_text(
        """
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Cash
    name: Cash
    account_type: ASSET
  - code: Expenses:Meals
    name: Meals
    account_type: EXPENSE
""".lstrip(),
        encoding="utf-8",
    )
    result = load_chart_of_accounts(coa_path)

    missing = missing_account_codes(result.accounts, ["Assets:Cash", "Expenses:Meals", "Expenses:Nope"])
    assert missing == ["Expenses:Nope"]

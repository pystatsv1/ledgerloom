from __future__ import annotations

import pandas as pd

from ledgerloom.project.reclass import RECLASS_TEMPLATE_COLUMNS, reclass_template_from_unmapped


def test_reclass_template_from_unmapped_columns_and_sorting() -> None:
    unmapped = pd.DataFrame(
        [
            {
                "entry_id": "b",
                "date": "2026-01-03",
                "original_description": "Rent",
                "original_amount": -1200.0,
                "suspense_account": "Expenses:Uncategorized",
            },
            {
                "entry_id": "a",
                "date": "2026-01-02",
                "original_description": "Coffee",
                "original_amount": -4.5,
                "suspense_account": "Expenses:Uncategorized",
            },
        ]
    )

    out = reclass_template_from_unmapped(unmapped)

    assert list(out.columns) == RECLASS_TEMPLATE_COLUMNS
    assert out["entry_id"].tolist() == ["a", "b"]
    assert out["reclass_account"].tolist() == ["", ""]
    assert out["note"].nunique() == 1
    assert out.loc[0, "description"] == "Coffee"
    assert out.loc[1, "description"] == "Rent"


def test_reclass_template_from_unmapped_empty_input() -> None:
    empty = pd.DataFrame(
        columns=[
            "entry_id",
            "date",
            "original_description",
            "original_amount",
            "suspense_account",
        ]
    )
    out = reclass_template_from_unmapped(empty)
    assert list(out.columns) == RECLASS_TEMPLATE_COLUMNS
    assert len(out) == 0

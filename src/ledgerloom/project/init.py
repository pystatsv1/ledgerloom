"""Project skeleton generator (``ledgerloom init``).

The init command is the "zero Python" on-ramp for LedgerLoom's practical tool:

* Create a standard folder layout.
* Drop versioned config templates with sensible defaults.
* Keep files stable across OSes (LF newlines).

This module intentionally avoids being clever. It writes a small, editable
starting project that passes :command:`ledgerloom check` even before the user
adds any input CSVs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


def _write_text_lf(path: Path, text: str) -> None:
    """Write UTF-8 text with LF newlines (stable across OSes)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    # IMPORTANT: newline="\n" prevents Windows from translating newlines.
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def default_period_today() -> str:
    """Return a YYYY-MM period string based on today's date."""

    return date.today().strftime("%Y-%m")


@dataclass(frozen=True)
class InitOptions:
    project_name: str
    period: str
    currency: str = "USD"


def create_project_skeleton(dest: Path, *, opts: InitOptions) -> list[Path]:
    """Create a LedgerLoom project skeleton.

    Args:
        dest: Destination directory to create (or populate if empty).
        opts: High-level project options.

    Returns:
        A list of paths created (relative to ``dest``).

    Raises:
        FileExistsError: If ``dest`` exists and is not empty.
    """

    dest = dest.resolve()
    if dest.exists():
        # Allow an existing empty directory.
        if any(dest.iterdir()):
            raise FileExistsError(
                f"Destination directory is not empty: {dest}. "
                "Choose a new path or empty the directory first."
            )
    else:
        dest.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []

    # Directory layout.
    (dest / "config").mkdir(parents=True, exist_ok=True)
    (dest / "config" / "mappings").mkdir(parents=True, exist_ok=True)
    (dest / "inputs" / opts.period).mkdir(parents=True, exist_ok=True)
    (dest / "outputs").mkdir(parents=True, exist_ok=True)

    # Placeholder files keep empty dirs visible in Git.
    _write_text_lf(dest / "config" / "mappings" / ".gitkeep", "")
    created.append(Path("config/mappings/.gitkeep"))
    _write_text_lf(dest / "inputs" / opts.period / ".gitkeep", "")
    created.append(Path(f"inputs/{opts.period}/.gitkeep"))

    # Chart of accounts template.
    coa_text = """\
schema_id: ledgerloom.chart_of_accounts.v1
accounts:
  - code: Assets:Cash
    name: Cash
    type: asset

  - code: Expenses:Uncategorized
    name: Uncategorized
    type: expense

  - code: Expenses:Meals
    name: Meals
    type: expense

  - code: Expenses:Groceries
    name: Groceries
    type: expense

  - code: Revenue:Other
    name: Other Income
    type: revenue
"""
    _write_text_lf(dest / "config" / "chart_of_accounts.yaml", coa_text)
    created.append(Path("config/chart_of_accounts.yaml"))

    # Project config template.
    yaml_text = f"""\
# LedgerLoom project configuration (v1)
#
# Edit this file in YAML (no Python required).
# Then run:
#   ledgerloom check --project .
#
# Drop source CSVs into: inputs/{opts.period}/

schema_id: ledgerloom.project_config.v1

project:
  name: {opts.project_name}
  period: {opts.period}
  currency: {opts.currency}

chart_of_accounts: config/chart_of_accounts.yaml

# If true, unmapped rows (posted to suspense) are treated as errors.
strict_unmapped: false

sources:
  # Bank-feed CSV adapter (v1). Add more sources over time.
  - source_type: bank_feed.v1
    name: Checking
    # Pattern is relative to inputs/<period>/
    file_pattern: "*.csv"
    default_account: Assets:Cash
    columns:
      date: Date
      description: Description
      amount: Amount
    # IMPORTANT: LedgerLoom does not guess date formats.
    # Common bank exports: "%m/%d/%Y" or "%Y-%m-%d".
    date_format: "%m/%d/%Y"
    amount_thousands_sep: ","
    amount_decimal_sep: "."
    invert_amount_sign: false
    suspense_account: Expenses:Uncategorized

    # Regex mapping rules (applied to the description).
    # If nothing matches, the transaction goes to the suspense account above.
    rules:
      - pattern: "(?i)restaurant|cafe|coffee"
        account: Expenses:Meals
      - pattern: "(?i)grocery|supermarket"
        account: Expenses:Groceries

outputs:
  root: outputs
"""
    _write_text_lf(dest / "ledgerloom.yaml", yaml_text)
    created.append(Path("ledgerloom.yaml"))

    # Minimal README to orient non-dev users.
    readme = f"""\
# {opts.project_name}

This folder is a LedgerLoom project.

## Quickstart

1) Put your CSVs in `inputs/{opts.period}/`
2) Edit `ledgerloom.yaml` and `config/chart_of_accounts.yaml`
3) Run the gatekeeper:

```bash
ledgerloom check --project .
```

Outputs:

* `outputs/check/{opts.period}/checks.md`
* `outputs/check/{opts.period}/staging.csv`
* `outputs/check/{opts.period}/staging_issues.csv`
"""
    _write_text_lf(dest / "README.md", readme)
    created.append(Path("README.md"))

    return created

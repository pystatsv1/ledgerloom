"""Project-level configuration and workflows.

The :mod:`ledgerloom.project` package is the start of LedgerLoom's "practical tool"
surface area: a versioned project config, loaders, and (later) CLI workflows.
"""

from __future__ import annotations

from .config import ProjectConfig
from .check import CheckIssue, CheckResult, run_check
from .coa import CoaLoadResult, load_chart_of_accounts, missing_account_codes, validate_coa
from .init import InitOptions, create_project_skeleton, default_period_today
from .build import BuildResult, default_run_id, run_build

__all__ = [
    "ProjectConfig",
    "CheckIssue",
    "CheckResult",
    "run_check",
    "CoaLoadResult",
    "load_chart_of_accounts",
    "validate_coa",
    "missing_account_codes",
    "InitOptions",
    "create_project_skeleton",
    "default_period_today",
    "BuildResult",
    "default_run_id",
    "run_build",
]

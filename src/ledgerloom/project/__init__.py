"""Project-level configuration and workflows.

The :mod:`ledgerloom.project` package is the start of LedgerLoom's "practical tool"
surface area: a versioned project config, loaders, and (later) CLI workflows.
"""

from __future__ import annotations

from .config import ProjectConfig

__all__ = [
    "ProjectConfig",
]

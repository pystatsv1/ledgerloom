"""
Top-level package for LedgerLoom.

Convenience re-exports:

- PROJECT_ROOT
- OUTPUTS_DIR
- get_local_docs_path, open_local_docs
"""

from importlib.metadata import PackageNotFoundError, version

from .docs_helper import get_local_docs_path, open_local_docs
from .paths import OUTPUTS_DIR, PROJECT_ROOT  # noqa: F401

__all__ = [
    "PROJECT_ROOT",
    "OUTPUTS_DIR",
    "__version__",
    "get_local_docs_path",
    "open_local_docs",
]

try:
    __version__ = version("ledgerloom")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

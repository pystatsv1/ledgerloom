from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from .paths import PROJECT_ROOT


def get_local_docs_path() -> Path:
    """Return the path to locally-built HTML docs (docs/build/html/index.html).

    Raises FileNotFoundError if the docs haven't been built yet.
    """
    p = PROJECT_ROOT / "docs" / "build" / "html" / "index.html"
    if not p.exists():
        raise FileNotFoundError(
            "Local HTML docs not found. Run `make docs` to build them."
        )
    return p


def _open_file_native(path: Path) -> bool:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            subprocess.check_call(["open", str(path)])
            return True
        subprocess.check_call(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def open_local_docs() -> None:
    """Open local HTML docs in the default browser."""
    p = get_local_docs_path()
    if _open_file_native(p):
        return
    webbrowser.open_new(p.as_uri())


def open_online_docs() -> None:
    """Open the Read the Docs site for LedgerLoom."""
    webbrowser.open_new("https://ledgerloom.readthedocs.io/en/latest/")

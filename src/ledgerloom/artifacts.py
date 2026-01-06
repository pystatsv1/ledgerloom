"""Deterministic artifact I/O helpers.

LedgerLoom chapters intentionally *own* their file I/O so readers can see
exactly what's written to disk. However, repeating the same low-level details
across chapters is error-prone (especially on Windows where newline translation
can change bytes and therefore hashes).

This module centralizes the boring-but-important parts:

* UTF-8 text with LF line endings
* stable JSON formatting (indent + sorted keys)
* stable CSV writing (either pandas DataFrames or dict rows)
* sha256 + byte counts for manifests

Chapters remain free to decide *what* they write. This module helps ensure they
write it the same way everywhere.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd


def ensure_dir(path: Path) -> None:
    """Ensure the parent directory for *path* exists."""

    path.parent.mkdir(parents=True, exist_ok=True)


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_text(path: Path, text: str, *, ensure_trailing_newline: bool = True) -> None:
    """Write UTF-8 text with LF newlines.

    If *ensure_trailing_newline* is True, appends a final ``\n`` if missing.
    """

    ensure_dir(path)
    if ensure_trailing_newline and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def dumps_json(obj: Any, *, indent: int = 2, sort_keys: bool = True) -> str:
    """Return a stable JSON string (no trailing newline)."""

    return json.dumps(obj, indent=indent, sort_keys=sort_keys)


def write_json(
    path: Path,
    obj: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_trailing_newline: bool = True,
) -> None:
    """Write stable JSON with LF newlines."""

    write_text(
        path,
        dumps_json(obj, indent=indent, sort_keys=sort_keys),
        ensure_trailing_newline=ensure_trailing_newline,
    )


def write_csv_dicts(
    path: Path,
    rows: Iterable[dict[str, Any]],
    *,
    fieldnames: Sequence[str],
) -> None:
    """Write CSV from dict rows with a stable header order and LF newlines."""

    ensure_dir(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_csv_df(path: Path, df: pd.DataFrame, *, columns: Sequence[str] | None = None) -> None:
    """Write a DataFrame to CSV with LF newlines.

    If *columns* is provided, it controls the output column order.
    """

    ensure_dir(path)
    csv_text = df.to_csv(index=False, columns=list(columns) if columns is not None else None, lineterminator="\n")
    # The string returned by pandas already contains \n line endings.
    write_text(path, csv_text, ensure_trailing_newline=False)


def manifest_items(
    outdir: Path,
    files: Sequence[Path],
    *,
    name_key: str = "name",
) -> list[dict[str, Any]]:
    """Build per-file manifest entries with sha256 + byte counts.

    *name_key* controls the field used for the relative filename (e.g. some
    chapters historically used "file" instead of "name").
    """

    items: list[dict[str, Any]] = []
    for p in files:
        rel = p.name
        try:
            rel = p.relative_to(outdir).as_posix()
        except Exception:
            rel = p.name
        items.append({name_key: rel, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    return items

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
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


# ---------------------------------------------------------------------------
# Trust Pipeline v1 schemas
# ---------------------------------------------------------------------------

# These IDs are written into chapter-level trust artifacts (run_meta.json and
# manifest.json). Keeping them as module-level constants makes the contract
# explicit and gives us room to introduce future versions without ambiguity.

MANIFEST_SCHEMA_V1 = "ledgerloom.manifest.v1"
RUN_META_SCHEMA_V1 = "ledgerloom.run_meta.v1"


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


def write_jsonl(
    path: Path,
    rows: Iterable[dict[str, Any]],
    *,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> None:
    """Write JSONL (one JSON object per line) with LF newlines.

    Notes
    -----
    - This function intentionally writes *bytes deterministically* across platforms.
    - Each row is dumped with compact separators (no spaces) and (optionally) sorted keys.
    """

    ensure_dir(path)
    # newline='\n' prevents Windows newline translation (\n -> \r\n).
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    sort_keys=sort_keys,
                    ensure_ascii=ensure_ascii,
                    separators=(",", ":"),
                )
            )
            f.write("\n")


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
    csv_text = df.to_csv(
        index=False,
        columns=list(columns) if columns is not None else None,
        lineterminator="\n",
    )
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
        items.append(
            {name_key: rel, "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        )
    return items


def specs_with_hashes(
    outdir: Path,
    specs: Sequence[Mapping[str, object]],
    *,
    name_key: str = "name",
    bytes_key: str = "bytes",
    sha_key: str = "sha256",
) -> list[dict[str, object]]:
    """Return a copy of each spec augmented with bytes + sha256 for the referenced file.

    The file path is resolved as ``outdir / spec[name_key]``.
    """

    out: list[dict[str, object]] = []
    for spec in specs:
        if name_key not in spec:
            raise KeyError(f"spec missing {name_key!r}: {spec}")
        name = str(spec[name_key])
        p = outdir / name
        d = dict(spec)
        d[bytes_key] = int(p.stat().st_size)
        d[sha_key] = sha256_file(p)
        out.append(d)
    return out


def _with_schema(obj: Any, schema: str) -> Any:
    """Return *obj* with a top-level ``schema`` field injected if missing.

    We avoid mutating caller objects. Only dict payloads are schema-tagged.
    If a different schema is already present, we leave it unchanged.
    """

    if not isinstance(obj, dict):
        return obj
    if obj.get("schema") == schema:
        return obj
    if "schema" in obj and obj["schema"] != schema:
        return obj
    out = dict(obj)
    out["schema"] = schema
    return out


def write_run_meta(path: Path, obj: Any) -> None:
    """Write ``run_meta.json`` with schema injection and deterministic formatting."""

    write_json(path, _with_schema(obj, RUN_META_SCHEMA_V1))


def write_manifest(path: Path, obj: Any) -> None:
    """Write ``manifest.json`` with schema injection and deterministic formatting."""

    write_json(path, _with_schema(obj, MANIFEST_SCHEMA_V1))


def artifacts_map(outdir: Path, artifact_names: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Return mapping-style manifest entries: ``{name: {bytes, sha256}}``."""

    out: dict[str, dict[str, Any]] = {}
    for name in artifact_names:
        p = outdir / name
        out[name] = {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
    return out


def manifest_items_prefixed(
    outdir: Path,
    artifact_names: Sequence[str],
    *,
    prefix: str,
    name_key: str = "path",
) -> list[dict[str, Any]]:
    """Build manifest items that record paths with a fixed prefix.

    Used for chapters that historically record paths like ``"ch085/<file>"``
    even though the files live at ``<outdir>/<file>``.
    """

    items: list[dict[str, Any]] = []
    for name in artifact_names:
        p = outdir / name
        items.append(
            {
                name_key: f"{prefix}/{name}",
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
        )
    return items

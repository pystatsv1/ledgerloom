"""Trust pipeline entrypoints.

This module provides a *single* canonical way to emit the two trust artifacts
written by chapters:

* ``run_meta.json`` — reproducible run metadata
* ``manifest.json`` — artifact manifest (hashes + sizes)

The helpers in :mod:`ledgerloom.artifacts` do the low-level deterministic I/O.
These functions coordinate them so chapters don't re-implement the same
plumbing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Mapping, Sequence, TypeAlias

from ledgerloom.artifacts import (
    manifest_items,
    specs_with_hashes,
    write_manifest,
    write_run_meta,
)


ManifestLike: TypeAlias = Mapping[str, Any] | Callable[[Path], Mapping[str, Any]]


def emit_trust_artifacts(
    outdir: Path,
    *,
    run_meta: Mapping[str, Any],
    manifest: ManifestLike,
    run_meta_name: str = "run_meta.json",
    manifest_name: str = "manifest.json",
) -> None:
    """Write chapter trust artifacts in a schema-aware, deterministic way.

    Parameters
    ----------
    outdir:
        Chapter output directory.
    run_meta:
        JSON-serializable run metadata payload (schema is injected if missing).
    manifest:
        JSON-serializable manifest payload (schema is injected if missing).

    Notes
    -----
    This function intentionally does *not* decide what the payloads contain.
    It only standardizes how the files are written (LF newlines, stable JSON,
    schema tags).
    """

    write_run_meta(outdir / run_meta_name, dict(run_meta))
    manifest_payload = manifest(outdir) if callable(manifest) else manifest
    write_manifest(outdir / manifest_name, dict(manifest_payload))


def run_meta_artifacts_from_names(
    outdir: Path, artifact_names: Sequence[str]
) -> list[dict[str, Any]]:
    """Build ``[{name, bytes, sha256}, ...]`` entries for ``run_meta.json``.

    Callers are responsible for excluding ``run_meta.json`` and ``manifest.json``
    themselves to avoid recursion.
    """

    files = [outdir / name for name in artifact_names]
    return manifest_items(outdir, files, name_key="name")


def manifest_artifacts_from_specs(
    outdir: Path,
    specs: Sequence[Mapping[str, object]],
    *,
    name_key: str = "name",
) -> list[dict[str, object]]:
    """Return ``specs`` augmented with ``bytes`` and ``sha256`` for each file."""

    return specs_with_hashes(outdir, specs, name_key=name_key)

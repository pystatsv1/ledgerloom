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
    artifacts_map,
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
def _iter_files_rel(run_root: Path, start: Path) -> list[str]:
    """Return POSIX relative paths for all files under *start*, sorted."""
    if not start.exists():
        return []
    rels: list[str] = []
    for p in start.rglob("*"):
        if p.is_file():
            rels.append(p.relative_to(run_root).as_posix())
    return sorted(rels)


def collect_run_artifacts(
    run_root: Path,
    *,
    include_dirs: Sequence[str] = ("source_snapshot", "check"),
    extra_artifacts: Sequence[str] = (),
) -> list[str]:
    """Collect artifact paths (relative to *run_root*) for a tool run.

    Notes
    -----
    - Returned paths are POSIX-style and sorted (stable across OS).
    - The trust directory is intentionally excluded by default to avoid self-hashing.
    """
    items: list[str] = []
    for d in include_dirs:
        items.extend(_iter_files_rel(run_root, run_root / d))

    for x in extra_artifacts:
        items.append(Path(x).as_posix().lstrip("./"))

    # De-dup while preserving stable ordering after final sort.
    return sorted(set(items))


def emit_run_trust_artifacts(
    run_root: Path,
    *,
    run_meta: Mapping[str, Any],
    include_dirs: Sequence[str] = ("source_snapshot", "check"),
    extra_artifacts: Sequence[str] = (),
    trust_dir_name: str = "trust",
) -> tuple[Path, Path, Path]:
    """Write trust artifacts (run_meta + manifest) for a tool run directory.

    The manifest hashes files inside *run_root* (typically the snapshot + check outputs),
    while the trust JSON files are written under *run_root/trust_dir_name*.
    """
    trust_dir = run_root / trust_dir_name
    trust_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths = collect_run_artifacts(
        run_root, include_dirs=include_dirs, extra_artifacts=extra_artifacts
    )
        # Manifest is content-addressed: it must not include execution-specific fields
    # like run_id or timestamps. Those belong in run_meta.json.
    manifest: ManifestLike = {
        "artifacts": artifacts_map(run_root, artifact_paths),
    }

    emit_trust_artifacts(trust_dir, run_meta=run_meta, manifest=manifest)
    return trust_dir, trust_dir / "run_meta.json", trust_dir / "manifest.json"

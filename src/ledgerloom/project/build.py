from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import shutil

from .config import ProjectConfig
from .check import CheckResult, run_check


@dataclass(frozen=True)
class BuildResult:
    run_id: str
    run_root: Path
    snapshot_root: Path
    check_outdir: Path
    check_result: CheckResult
    snapshotted_files: tuple[Path, ...]


def default_run_id(now: datetime | None = None) -> str:
    """Return a filesystem-friendly run id.

    Format: YYYYMMDD-HHMMSS (local time).
    """
    now = datetime.now() if now is None else now
    return now.strftime("%Y%m%d-%H%M%S")


def _resolve_under(project_root: Path, p: Path) -> Path:
    return p if p.is_absolute() else (project_root / p)


def _iter_files(root_dir: Path) -> Iterable[Path]:
    """Yield all files under root_dir (recursive), deterministic by path."""
    if not root_dir.exists():
        return []
    files = [p for p in root_dir.rglob("*") if p.is_file()]
    return sorted(files, key=lambda x: x.as_posix())


def _snapshot_copy(*, project_root: Path, src: Path, snapshot_root: Path) -> Path:
    rel = src.relative_to(project_root)
    dest = snapshot_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return rel


def snapshot_sources(
    *,
    project_root: Path,
    cfg_file: Path,
    cfg: ProjectConfig,
    inputs_dir: Path,
    run_root: Path,
    enabled: bool = True,
) -> tuple[Path, ...]:
    """Copy inputs + configs into outputs/<run_id>/source_snapshot/.

    Snapshotting makes a run self-contained and reproducible even if the user
    later edits or deletes their source files.
    """
    snapshot_root = run_root / "source_snapshot"
    snapshot_root.mkdir(parents=True, exist_ok=True)

    if not enabled:
        return tuple()

    files: list[Path] = []

    # Always include the project config file.
    if cfg_file.exists():
        files.append(cfg_file)

    # Include config directory if present (COA, mappings, etc).
    cfg_dir = project_root / "config"
    files.extend(_iter_files(cfg_dir))

    # Include period inputs matching configured source patterns.
    if inputs_dir.exists():
        gitkeep = inputs_dir / ".gitkeep"
        if gitkeep.exists():
            files.append(gitkeep)

        for src_cfg in cfg.sources:
            matched = sorted(inputs_dir.glob(src_cfg.file_pattern))
            files.extend(matched)

    # De-dup + deterministic ordering by relative path.
    unique: dict[str, Path] = {}
    for f in files:
        try:
            rel = f.relative_to(project_root).as_posix()
        except ValueError:
            # Should not happen for project-local files; skip if it does.
            continue
        unique[rel] = f

    copied: list[Path] = []
    for rel in sorted(unique.keys()):
        copied.append(_snapshot_copy(project_root=project_root, src=unique[rel], snapshot_root=snapshot_root))

    return tuple(copied)


def run_build(
    *,
    project_root: Path,
    config_path: Path | None = None,
    inputs_dir: Path | None = None,
    run_id: str | None = None,
    snapshot: bool = True,
) -> BuildResult:
    """Create a run directory with snapshot + check artifacts.

    PR07a scope:
    - Create outputs/<run_id>/
    - Snapshot source files into outputs/<run_id>/source_snapshot/
    - Run gatekeeper check into outputs/<run_id>/check/
    """
    project_root = project_root.resolve()
    cfg_file = (project_root / "ledgerloom.yaml") if config_path is None else config_path
    if not cfg_file.is_absolute():
        cfg_file = project_root / cfg_file

    cfg = ProjectConfig.load_yaml(cfg_file)

    # Resolve inputs dir default.
    inputs_dir = (project_root / "inputs" / cfg.project.period) if inputs_dir is None else inputs_dir
    inputs_dir = _resolve_under(project_root, inputs_dir).resolve()

    # Resolve outputs run root.
    run_id = default_run_id() if run_id is None else run_id
    run_root = (project_root / cfg.outputs.root / run_id).resolve()
    if run_root.exists() and any(run_root.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {run_root} (choose a different --run-id)"
        )
    run_root.mkdir(parents=True, exist_ok=True)

    # Snapshot sources first so the run is self-contained even if check fails.
    snapshotted = snapshot_sources(
        project_root=project_root,
        cfg_file=cfg_file,
        cfg=cfg,
        inputs_dir=inputs_dir,
        run_root=run_root,
        enabled=snapshot,
    )
    snapshot_root = run_root / "source_snapshot"
    check_outdir = run_root / "check"

    check_result = run_check(
        project_root=project_root,
        config_path=cfg_file,
        inputs_dir=inputs_dir,
        outdir=check_outdir,
    )

    return BuildResult(
        run_id=run_id,
        run_root=run_root,
        snapshot_root=snapshot_root,
        check_outdir=check_outdir,
        check_result=check_result,
        snapshotted_files=snapshotted,
    )

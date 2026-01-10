"""Project path helpers.

The practical-tool pipeline needs a small, stable API surface for:

- resolving project-relative paths,
- determining the canonical run directory layout, and
- iterating files deterministically (stable ordering across OS).

Keeping these helpers centralized avoids "god-function" pressure in
``ledgerloom.project.build`` as we expand the practical tool to new
accounting workflows (AR/AP/Inventory, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def resolve_under(project_root: Path, path: Path) -> Path:
    """Resolve a path, treating relative paths as relative to project_root."""

    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    return (project_root / p).resolve()


def resolve_config_path(project_root: Path, config_path: Path | None) -> Path:
    """Return the config file path (defaults to ``ledgerloom.yaml``)."""

    def _missing_default_config_message(cfg: Path) -> str:
        msg = (
            "No ledgerloom.yaml found in the project root.\n\n"
            f"Searched: {cfg}\n"
            f"Project root: {project_root.resolve()}\n\n"
            "Tip: ledgerloom build/check expect a project directory created by 'ledgerloom init'.\n"
            "Example:\n"
            "  ledgerloom init my_books\n"
            "  ledgerloom build --project my_books --run-id run-a\n"
        )
        if (project_root / "pyproject.toml").exists() and (project_root / "src" / "ledgerloom").exists():
            msg += (
                "\nIt looks like you're running from the LedgerLoom source repository.\n"
                "The repository root is not a LedgerLoom project directory.\n"
            )
        return msg

    if config_path is None:
        cfg = (project_root / "ledgerloom.yaml").resolve()
        if not cfg.exists():
            raise FileNotFoundError(_missing_default_config_message(cfg))
        return cfg

    cfg = resolve_under(project_root, Path(config_path))
    if not cfg.exists():
        # Common UX case: user runs from repo root (or wrong folder) and relies on
        # the default config name.
        default_cfg = (project_root / "ledgerloom.yaml").resolve()
        if cfg == default_cfg:
            raise FileNotFoundError(_missing_default_config_message(cfg))
        raise FileNotFoundError(f"Config file not found: {cfg}")
    return cfg

def resolve_inputs_dir(project_root: Path, *, period: str, inputs_dir: Path | None) -> Path:
    """Return the inputs directory.

    If inputs_dir is not supplied, default to ``inputs/<period>/``.
    """

    if inputs_dir is None:
        return (project_root / "inputs" / period).resolve()
    return resolve_under(project_root, Path(inputs_dir))



def resolve_run_root(project_root: Path, *, outputs_root: str, run_id: str) -> Path:
    """Resolve the output run directory (outputs_root/run_id) under the project."""
    out_root = (project_root / outputs_root).resolve()
    return out_root / run_id

def default_run_id(now: datetime | None = None) -> str:
    """Default run identifier.

    Uses a UTC timestamp to keep things deterministic across timezones.
    """

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.strftime("run-%Y%m%dT%H%M%SZ")


@dataclass(frozen=True, slots=True)
class RunLayout:
    """Canonical run directory layout."""

    run_root: Path
    check_dir: Path
    snapshot_dir: Path
    trust_dir: Path
    artifacts_dir: Path


def run_layout(run_root: Path) -> RunLayout:
    """Return the canonical directory layout for a run."""

    rr = Path(run_root).resolve()
    return RunLayout(
        run_root=rr,
        check_dir=rr / "check",
        snapshot_dir=rr / "source_snapshot",
        trust_dir=rr / "trust",
        artifacts_dir=rr / "artifacts",
    )


def iter_files(root_dir: Path) -> list[Path]:
    """Yield all files under root_dir (recursive), deterministic by path."""

    root = Path(root_dir)
    if not root.exists():
        return []
    files: list[Path] = [p for p in root.rglob("*") if p.is_file()]
    return sorted(files, key=lambda p: p.as_posix())


def iter_glob(root_dir: Path, pattern: str) -> list[Path]:
    """Deterministic glob of files within root_dir."""

    root = Path(root_dir)
    matches: Iterable[Path] = root.glob(pattern)
    return sorted((p for p in matches if p.is_file()), key=lambda p: p.as_posix())

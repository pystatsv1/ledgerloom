from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ledgerloom import __version__ as ledgerloom_version
from ledgerloom.artifacts import write_csv_df
from ledgerloom.engine import LedgerEngine
from ledgerloom.ingest.csv_bank_feed import ingest_bank_feed_csv
from ledgerloom.scenarios import bookset_v1
from ledgerloom.trust.pipeline import emit_run_trust_artifacts

from .check import CheckResult, run_check
from .config import ProjectConfig
from .paths import (
    default_run_id,
    iter_files,
    resolve_config_path,
    resolve_inputs_dir,
    resolve_run_root,
    run_layout,
)


@dataclass(frozen=True)
class BuildResult:
    run_id: str
    run_root: Path
    snapshot_root: Path
    check_outdir: Path
    trust_outdir: Path
    check_result: CheckResult
    snapshotted_files: tuple[Path, ...]


def _write_postings_csv(*, cfg: ProjectConfig, inputs_dir: Path, run_root: Path) -> Path:
    """Materialize postings.csv under outputs/<run_id>/artifacts/.

    This is the first "real" accounting artifact for the practical tool.
    We intentionally re-ingest the configured sources (same call signature
    used by ``run_check``) and then derive the postings fact table.
    """

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for src in cfg.sources:
        files = sorted(inputs_dir.glob(src.file_pattern)) if inputs_dir.exists() else []
        for p in files:
            # Reuse the same ingest call signature that run_check() uses.
            res = ingest_bank_feed_csv(p, src, strict=False)
            entries.extend(res.entries)

    eng = LedgerEngine()
    postings = eng.postings_fact_table(entries)

    # Ensure stable column order even when the table is empty.
    schema = eng.gl_schema_description()
    cols = [c["name"] for c in schema["tables"]["postings"]["columns"]]

    out_path = layout.artifacts_dir / "postings.csv"
    write_csv_df(out_path, postings, columns=cols)
    return out_path






def _write_trial_balance_csv(*, cfg: ProjectConfig, inputs_dir: Path, run_root: Path) -> Path:
    """Materialize trial_balance.csv under outputs/<run_id>/artifacts/.

    This is a compact trial balance derived from postings:

    * account — full account name
    * root — top-level root (Assets/Liabilities/Equity/Revenue/Expenses)
    * balance — signed balance using LedgerLoom's canonical sign convention
    """

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for src in cfg.sources:
        files = sorted(inputs_dir.glob(src.file_pattern)) if inputs_dir.exists() else []
        for p in files:
            # Reuse the same ingest call signature that run_check() uses.
            res = ingest_bank_feed_csv(p, src, strict=False)
            entries.extend(res.entries)

    eng = LedgerEngine()
    postings = eng.postings_fact_table(entries)
    tb = bookset_v1.trial_balance(postings)

    out_path = layout.artifacts_dir / "trial_balance.csv"
    write_csv_df(out_path, tb, columns=["account", "root", "balance"])
    return out_path
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
    snapshot_root = run_layout(run_root).snapshot_dir
    snapshot_root.mkdir(parents=True, exist_ok=True)

    if not enabled:
        return tuple()

    files: list[Path] = []

    # Always include the project config file.
    if cfg_file.exists():
        files.append(cfg_file)

    # Include config directory if present (COA, mappings, etc).
    cfg_dir = project_root / "config"
    files.extend(iter_files(cfg_dir))

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
    cfg_file = resolve_config_path(project_root, config_path)
    cfg = ProjectConfig.load_yaml(cfg_file)

    # Resolve inputs dir default.
    inputs_dir = resolve_inputs_dir(project_root, period=cfg.project.period, inputs_dir=inputs_dir)

    # Resolve outputs run root.
    run_id = default_run_id() if run_id is None else run_id
    run_root = resolve_run_root(project_root, outputs_root=cfg.outputs.root, run_id=run_id)
    layout = run_layout(run_root)
    if layout.run_root.exists() and any(layout.run_root.iterdir()):
        raise FileExistsError(
            f"Run directory already exists and is not empty: {layout.run_root} (choose a different --run-id)"
        )
    layout.run_root.mkdir(parents=True, exist_ok=True)

    # Snapshot sources first so the run is self-contained even if check fails.
    snapshotted = snapshot_sources(
        project_root=project_root,
        cfg_file=cfg_file,
        cfg=cfg,
        inputs_dir=inputs_dir,
        run_root=layout.run_root,
        enabled=snapshot,
    )
    snapshot_root = layout.snapshot_dir
    check_outdir = layout.check_dir

    check_result = run_check(
        project_root=project_root,
        config_path=cfg_file,
        inputs_dir=inputs_dir,
        outdir=check_outdir,
    )

    extra_artifacts: tuple[str, ...] = tuple()
    if not check_result.has_errors:
        # After check passes: ingest -> entries -> postings -> trial balance.
        _write_postings_csv(cfg=cfg, inputs_dir=inputs_dir, run_root=run_root)
        _write_trial_balance_csv(cfg=cfg, inputs_dir=inputs_dir, run_root=run_root)
        extra_artifacts = ("artifacts/postings.csv", "artifacts/trial_balance.csv")

    trust_outdir, _, _ = emit_run_trust_artifacts(
        run_root,
        run_meta={
            "module": "ledgerloom.project.build",
            "run_id": run_id,
            "ledgerloom_version": ledgerloom_version,
            "project_name": cfg.project.name,
            "period": cfg.project.period,
            "currency": cfg.project.currency,
            "config_schema": cfg.schema_id,
        },
        include_dirs=("source_snapshot", "check"),
        extra_artifacts=extra_artifacts,
    )

    return BuildResult(
        run_id=run_id,
        run_root=run_root,
        snapshot_root=snapshot_root,
        check_outdir=check_outdir,
        trust_outdir=trust_outdir,
        check_result=check_result,
        snapshotted_files=snapshotted,
    )

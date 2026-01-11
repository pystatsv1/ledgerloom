from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
import pandas as pd

from ledgerloom import __version__ as ledgerloom_version
from ledgerloom.artifacts import write_csv_df
from ledgerloom.core import Entry, Posting
from ledgerloom.engine import LedgerEngine
from ledgerloom.scenarios import bookset_v1
from ledgerloom.trust.pipeline import emit_run_trust_artifacts

from .check import CheckResult, run_check
from .config import ProjectConfig
from .reclass import RECLASS_TEMPLATE_COLUMNS, reclass_template_from_unmapped
from .paths import (
    default_run_id,
    iter_files,
    resolve_config_path,
    resolve_inputs_dir,
    resolve_run_root,
    run_layout,    resolve_source_files,
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



class BuildAbortError(RuntimeError):
    """Raised when a build must stop due to user-configured strictness.

    The run folder is kept on disk so the user can review check artifacts and
    fix mappings.
    """

    def __init__(self, message: str, *, run_root: Path, check_outdir: Path) -> None:
        super().__init__(message)
        self.run_root = run_root
        self.check_outdir = check_outdir
        self.trust_outdir: Path | None = None

def _slug_source_name(name: str) -> str:
    """Best-effort slug for stable entry_id synthesis."""

    return "".join(c.lower() if c.isalnum() else "_" for c in str(name)).strip("_")


def _parse_money(raw: str) -> Decimal:
    s = str(raw).strip()
    if s == "":
        return Decimal("0")
    return Decimal(s)


def _entries_from_staging_postings(*, staging_postings_csv: Path) -> list[Entry]:
    """Compile check's staging_postings.csv into Entry objects.

    This is the core "compiler" move:

    - `ledgerloom check` produces a canonical posting-line IR (staging_postings.csv)
    - `ledgerloom build` compiles that IR into postings/TB/statements

    This keeps build multi-source without re-parsing every input CSV twice.
    """

    df = pd.read_csv(staging_postings_csv, keep_default_na=False, dtype=str)

    required = [
        "source_name",
        "source_path",
        "source_row_number",
        "entry_id",
        "date",
        "narration",
        "account",
        "debit",
        "credit",
        "entry_kind",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "staging_postings.csv missing required columns: " + ", ".join(missing) + f" ({staging_postings_csv})"
        )

    # Deterministic order: use the CSV row order that `check` emits.
    group_cols = ["source_name", "source_path", "entry_id", "date", "narration", "entry_kind"]

    entries: list[Entry] = []
    for _, g in df.groupby(group_cols, sort=False):
        source_name = g["source_name"].iloc[0]
        source_path = g["source_path"].iloc[0]
        raw_entry_id = g["entry_id"].iloc[0]
        dt = date.fromisoformat(g["date"].iloc[0])
        narration = g["narration"].iloc[0]
        entry_kind = g["entry_kind"].iloc[0]

        # Ensure entry_id is stable + globally unique for the engine.
        entry_id = raw_entry_id
        if ":" not in entry_id:
            entry_id = f"journal:{_slug_source_name(source_name)}:{Path(source_path).name}:{raw_entry_id}"

        # Aggregate row numbers for traceability (string join keeps it human-readable).
        row_nos = ",".join(str(x) for x in g["source_row_number"].tolist() if str(x).strip() != "")

        meta = {
            "entry_id": entry_id,
            "entry_kind": entry_kind,
            "source_name": source_name,
            "source_file": Path(source_path).name,
            "source_path": source_path,
            "source_row_numbers": row_nos,
        }

        postings: list[Posting] = []
        for _, r in g.iterrows():
            dr = abs(_parse_money(r["debit"]))
            cr = abs(_parse_money(r["credit"]))
            if (dr > 0) == (cr > 0):
                raise ValueError(
                    "staging_postings row must have exactly one of debit/credit non-zero "
                    f"(entry_id={raw_entry_id}, account={r['account']}, debit={r['debit']!r}, credit={r['credit']!r})"
                )
            postings.append(Posting(account=r["account"], debit=dr, credit=cr))

        entries.append(Entry(dt=dt, narration=narration, postings=postings, meta=meta))

    return entries


def _derive_postings(*, entries: list) -> tuple[LedgerEngine, object]:
    """Derive the postings fact table from entries."""

    eng = LedgerEngine()
    postings = eng.postings_fact_table(entries)
    return eng, postings




def _write_entries_csv(*, entries: list[Entry], run_root: Path) -> Path:
    """Materialize entries.csv under outputs/<run_id>/artifacts/.

    This is a canonical "journal lines" artifact derived from Entry objects.
    It is intended for workbook-style workflows where students prepare their
    entries in a spreadsheet and LedgerLoom verifies invariants downstream.

    Row contract (one row per posting line):

    - entry_id: stable globally unique entry id
    - date: ISO date (YYYY-MM-DD)
    - narration: entry header narration
    - entry_kind: e.g. bank_feed, journal, adjustment (from check IR)
    - line_no: 1-based line number within the entry
    - account: posting account
    - debit, credit: positive numbers (exactly one non-zero)
    - source_name/source_file/source_row_numbers: traceability (may be blank)
    """

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    cols = [
        "entry_id",
        "date",
        "narration",
        "entry_kind",
        "line_no",
        "account",
        "debit",
        "credit",
        "source_name",
        "source_file",
        "source_row_numbers",
    ]

    rows: list[dict[str, object]] = []
    for e in entries:
        meta = dict(getattr(e, "meta", {}) or {})
        entry_id = str(meta.get("entry_id") or "")
        entry_kind = str(meta.get("entry_kind") or "")
        source_name = str(meta.get("source_name") or "")
        source_file = str(meta.get("source_file") or "")
        source_rows = str(meta.get("source_row_numbers") or "")

        for i, p in enumerate(e.postings, start=1):
            rows.append(
                {
                    "entry_id": entry_id,
                    "date": e.dt.isoformat(),
                    "narration": e.narration,
                    "entry_kind": entry_kind,
                    "line_no": i,
                    "account": p.account,
                    "debit": str(p.debit),
                    "credit": str(p.credit),
                    "source_name": source_name,
                    "source_file": source_file,
                    "source_row_numbers": source_rows,
                }
            )

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        df = pd.DataFrame(columns=cols)

    out_path = layout.artifacts_dir / "entries.csv"
    write_csv_df(out_path, df, columns=cols)
    return out_path

def _write_postings_csv(*, eng: LedgerEngine, postings: object, run_root: Path) -> Path:
    """Materialize postings.csv under outputs/<run_id>/artifacts/."""

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Ensure stable column order even when the table is empty.
    schema = eng.gl_schema_description()
    cols = [c["name"] for c in schema["tables"]["postings"]["columns"]]

    out_path = layout.artifacts_dir / "postings.csv"
    write_csv_df(out_path, postings, columns=cols)
    return out_path


def _write_trial_balance_csv(*, tb: object, run_root: Path) -> Path:
    """Materialize trial_balance.csv under outputs/<run_id>/artifacts/.

    Contract:
    - account: full account name
    - root: top-level root (Assets/Liabilities/Equity/Revenue/Expenses)
    - balance: signed balance (LedgerLoom canonical sign convention)
    """

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    out_path = layout.artifacts_dir / "trial_balance.csv"
    write_csv_df(out_path, tb, columns=["account", "root", "balance"])
    return out_path


def _write_statements_csv(*, tb: object, run_root: Path) -> tuple[Path, Path]:
    """Materialize income_statement.csv + balance_sheet.csv from the trial balance."""

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    income = bookset_v1.income_statement(tb)
    balance = bookset_v1.balance_sheet_adjusted(tb)

    income_path = layout.artifacts_dir / "income_statement.csv"
    balance_path = layout.artifacts_dir / "balance_sheet.csv"
    write_csv_df(income_path, income, columns=["metric", "amount"])
    write_csv_df(balance_path, balance, columns=["metric", "amount"])
    return income_path, balance_path


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
            matched = resolve_source_files(
                project_root=project_root,
                inputs_dir=inputs_dir,
                file_pattern=src_cfg.file_pattern,
                period=cfg.project.period,
            )
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



UNMAPPED_COLUMNS: list[str] = [
    "entry_id",
    "date",
    "source_name",
    "source_file",
    "source_row_number",
    "original_description",
    "original_amount",
    "debit_account",
    "credit_account",
    "suspense_account",
    "suggested_pattern",
    "suggested_rule_yaml",
]


def _write_unmapped_csv(*, unmapped_csv: Path, run_root: Path) -> tuple[Path, pd.DataFrame]:
    """Write artifacts/unmapped.csv (copy of check's unmapped.csv).

    The check workflow produces a rich ``unmapped.csv`` (including suggested
    patterns / rules). ``ledgerloom build`` copies it into the auditable run
    folder so accountants don't have to jump between directories.
    """

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
    out_path = layout.artifacts_dir / "unmapped.csv"

    try:
        df = pd.read_csv(unmapped_csv, keep_default_na=False)
    except FileNotFoundError:
        df = pd.DataFrame(columns=UNMAPPED_COLUMNS)

    # Ensure stable columns even if the CSV is empty or missing some optional cols.
    if df.empty and len(df.columns) == 0:
        df = pd.DataFrame(columns=UNMAPPED_COLUMNS)
    for c in UNMAPPED_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    df = df[UNMAPPED_COLUMNS]
    write_csv_df(out_path, df, columns=UNMAPPED_COLUMNS)
    return out_path, df


def _write_reclass_template_csv(*, unmapped_csv: Path, run_root: Path) -> Path:
    """Write artifacts/reclass_template.csv based on artifacts/unmapped.csv.

    This keeps the accountant workflow close to the auditable run folder produced
    by `ledgerloom build`, while reusing the shared column schema and generator.
    """

    layout = run_layout(run_root)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
    out_path = layout.artifacts_dir / "reclass_template.csv"

    try:
        unmapped_df = pd.read_csv(unmapped_csv, keep_default_na=False)
    except FileNotFoundError:
        # Be defensive: treat missing unmapped.csv as "no unmapped rows".
        unmapped_df = pd.DataFrame(
            columns=[
                "entry_id",
                "date",
                "original_description",
                "original_amount",
                "suspense_account",
            ]
        )

    reclass_df = reclass_template_from_unmapped(unmapped_df)

    write_csv_df(
        out_path,
        reclass_df,
        columns=RECLASS_TEMPLATE_COLUMNS,
    )
    return out_path

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

    # Exception workflow artifacts live under artifacts/ so they travel with the run.
    # We still stop early if the check surfaced non-unmapped errors.
    errors_other_than_unmapped = any(
        (i.severity == "error" and i.code != "unmapped_suspense") for i in check_result.issues
    )

    abort_exc: BuildAbortError | None = None
    extra_artifacts: tuple[str, ...] = tuple()

    if not errors_other_than_unmapped:
        # Always materialize exception workflow helpers into artifacts/ (even if
        # strict_unmapped later aborts).
        unmapped_art_path, unmapped_df = _write_unmapped_csv(
            unmapped_csv=check_outdir / "unmapped.csv",
            run_root=run_root,
        )
        _write_reclass_template_csv(unmapped_csv=unmapped_art_path, run_root=run_root)

        has_unmapped = not unmapped_df.empty

        if cfg.strict_unmapped and has_unmapped:
            extra_artifacts = (
                "artifacts/unmapped.csv",
                "artifacts/reclass_template.csv",
            )
            abort_exc = BuildAbortError(
                "Build aborted: unmapped rows found and strict_unmapped is true. "
                "See check/unmapped.csv and artifacts/reclass_template.csv.",
                run_root=run_root,
                check_outdir=check_outdir,
            )
        elif not check_result.has_errors:
            # After check passes:
            #   check IR -> entries -> postings -> trial balance -> statements
            entries = _entries_from_staging_postings(
                staging_postings_csv=check_outdir / "staging_postings.csv",
            )
            eng, postings = _derive_postings(entries=entries)
            tb = bookset_v1.trial_balance(postings)

            _write_postings_csv(eng=eng, postings=postings, run_root=run_root)
            _write_trial_balance_csv(tb=tb, run_root=run_root)
            _write_statements_csv(tb=tb, run_root=run_root)

            extra_artifacts = (
                "artifacts/postings.csv",
                "artifacts/trial_balance.csv",
                "artifacts/income_statement.csv",
                "artifacts/balance_sheet.csv",
                "artifacts/unmapped.csv",
                "artifacts/reclass_template.csv",
            )
        else:
            # Check had errors, but only unmapped_suspense warnings/errors; keep the run folder.
            extra_artifacts = (
                "artifacts/unmapped.csv",
                "artifacts/reclass_template.csv",
            )
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
            "build_profile": cfg.build_profile,
        },
        include_dirs=("source_snapshot", "check"),
        extra_artifacts=extra_artifacts,
    )

    if abort_exc is not None:
        abort_exc.trust_outdir = trust_outdir
        raise abort_exc

    return BuildResult(
        run_id=run_id,
        run_root=run_root,
        snapshot_root=snapshot_root,
        check_outdir=check_outdir,
        trust_outdir=trust_outdir,
        check_result=check_result,
        snapshotted_files=snapshotted,
    )

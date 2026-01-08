"""Regenerate golden files for deterministic chapter outputs.

This repo uses small *golden file* fixtures under ``tests/golden`` to guard
against cross-platform drift (CRLF vs LF, JSON key ordering, etc.).

This script runs selected chapter modules and copies the expected files into
their corresponding golden directories.

Default behavior is conservative:
  - only overwrite files that already exist in the golden directory
  - fail if an expected golden file is missing from the generated output

Examples
--------

Regenerate all golden files (for the chapters that have a golden folder):

    python scripts/regen_goldens.py

Regenerate only ch01 + ch02:

    python scripts/regen_goldens.py --chapters ch01 ch02

Keep the generated work directory for inspection:

    python scripts/regen_goldens.py --keep-workdir
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChapterTarget:
    """A mapping from a golden directory name to a chapter module."""

    golden_dir: str
    module: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _discover_targets(repo_root: Path) -> list[ChapterTarget]:
    """Discover runnable targets based on ``tests/golden``.

    We intentionally key off what the repo *already* treats as golden to avoid
    accidentally adding new fixtures (which can bloat the repo or add noise).
    """

    golden_root = repo_root / "tests" / "golden"
    if not golden_root.exists():
        return []

    chapters_dir = repo_root / "src" / "ledgerloom" / "chapters"
    chapter_files = [p for p in chapters_dir.glob("ch*.py") if p.is_file()]

    targets: list[ChapterTarget] = []
    for d in sorted(p for p in golden_root.iterdir() if p.is_dir()):
        name = d.name

        # Special-case: the Chapter 03 COA schema chapter intentionally writes
        # to "ch03AccountsSchema" for readability.
        if name == "ch03AccountsSchema":
            targets.append(
                ChapterTarget(golden_dir=name, module="ledgerloom.chapters.ch03_chart_of_accounts_schema")
            )
            continue

        # Most chapters follow "<golden_dir>_<slug>.py".
        matches = [p for p in chapter_files if p.stem.startswith(name + "_")]
        if len(matches) != 1:
            # If we can't map it confidently, skip rather than guess.
            continue

        mod = f"ledgerloom.chapters.{matches[0].stem}"
        targets.append(ChapterTarget(golden_dir=name, module=mod))

    return targets


def _run_chapter(repo_root: Path, module: str, out_root: Path, seed: int) -> Path:
    """Run a chapter module and return the single output directory created."""

    cmd = [
        sys.executable,
        "-m",
        module,
        "--outdir",
        str(out_root),
        "--seed",
        str(seed),
    ]

    env = dict(os.environ)
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")

    subprocess.check_call(cmd, cwd=repo_root, env=env)

    subdirs = sorted([p for p in out_root.iterdir() if p.is_dir()])
    if len(subdirs) != 1:
        names = ", ".join(p.name for p in subdirs)
        raise SystemExit(
            f"Expected exactly 1 output directory for {module}, got {len(subdirs)}: {names}"
        )
    return subdirs[0]


def _copy_over_existing_files(*, src_dir: Path, golden_dir: Path) -> list[str]:
    updated: list[str] = []

    golden_files = [p for p in golden_dir.iterdir() if p.is_file()]
    if not golden_files:
        raise SystemExit(f"Golden directory has no files: {golden_dir.as_posix()}")

    for dst in sorted(golden_files):
        src = src_dir / dst.name
        if not src.exists():
            raise SystemExit(
                f"Missing expected generated file '{dst.name}' in {src_dir.as_posix()}"
            )
        shutil.copyfile(src, dst)
        updated.append(dst.name)

    return updated


def main() -> int:
    repo_root = _repo_root()
    targets = _discover_targets(repo_root)
    if not targets:
        raise SystemExit("No golden targets discovered under tests/golden")

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--chapters",
        nargs="*",
        default=None,
        help=(
            "Golden directory names to regenerate (e.g. ch01 ch02 ch07 ch03AccountsSchema). "
            "Default: all discovered goldens."
        ),
    )
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="Optional work directory for generated outputs (default: temp dir).",
    )
    ap.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Do not delete the work directory (useful for debugging).",
    )
    args = ap.parse_args()

    wanted = None
    if args.chapters is not None:
        wanted = {c.strip() for c in args.chapters if c.strip()}

    selected = [t for t in targets if wanted is None or t.golden_dir in wanted]
    if not selected:
        raise SystemExit("No matching targets. Try: --chapters " + " ".join(t.golden_dir for t in targets))

    if args.workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="ledgerloom_regen_goldens_"))
        owns_workdir = True
    else:
        workdir = args.workdir
        workdir.mkdir(parents=True, exist_ok=True)
        owns_workdir = False

    try:
        golden_root = repo_root / "tests" / "golden"
        print(f"Workdir: {workdir}")
        print(f"Seed: {args.seed}")

        for t in selected:
            print(f"\n== {t.golden_dir} ({t.module}) ==")
            out_root = workdir / t.golden_dir
            if out_root.exists():
                shutil.rmtree(out_root)
            out_root.mkdir(parents=True, exist_ok=True)

            produced_dir = _run_chapter(repo_root, t.module, out_root, seed=int(args.seed))
            updated = _copy_over_existing_files(
                src_dir=produced_dir,
                golden_dir=golden_root / t.golden_dir,
            )
            print("Updated:")
            for name in updated:
                print(f"  - {t.golden_dir}/{name}")

        print("\nDone.")
        return 0
    finally:
        if args.keep_workdir:
            print(f"Kept workdir: {workdir}")
        elif owns_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

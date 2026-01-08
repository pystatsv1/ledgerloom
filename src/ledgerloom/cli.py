from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import ledgerloom
from ledgerloom.docs_helper import open_online_docs
from ledgerloom.project.check import run_check


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level LedgerLoom CLI parser.

    PR05 goal: present a product-style CLI with subcommands while preserving
    the existing --version flag behavior.

    Subcommands are intentionally minimal here (init/build/report are stubs)
    and will be implemented in later PRs.
    """
    p = argparse.ArgumentParser(
        prog="ledgerloom",
        description="LedgerLoom practical tool CLI (init/check/build/report) plus utilities.",
    )

    # Keep existing top-level utilities.
    p.add_argument("--version", action="store_true", help="Print version and exit.")
    p.add_argument("--paths", action="store_true", help="Print important paths.")
    p.add_argument(
        "--docs",
        choices=["local", "online"],
        help="Open documentation (local requires `make docs`).",
    )

    sub = p.add_subparsers(dest="command")

    # PR06 will implement init; keep placeholder to establish UX + help.
    sub.add_parser("init", help="Create a new project skeleton (PR06)")

    # PR04 implemented check; wire it into the product CLI.
    c = sub.add_parser("check", help="Stage + validate inputs (gatekeeper workflow)")
    c.add_argument(
        "--project",
        default=".",
        help="Project root containing ledgerloom.yaml (default: current directory).",
    )
    c.add_argument(
        "--config",
        default="ledgerloom.yaml",
        help="Config file path (relative to --project unless absolute).",
    )
    c.add_argument(
        "--inputs",
        default=None,
        help="Override inputs directory (default: inputs/<period>/).",
    )
    c.add_argument(
        "--outdir",
        default=None,
        help="Override output directory for check artifacts.",
    )

    # PR07 will implement build; keep placeholder to establish UX + help.
    sub.add_parser("build", help="Build postings + statements + trust artifacts (PR07)")

    # Reporting UX placeholder (could later become report/open/run exports).
    sub.add_parser("report", help="Open or export reports for a run (future)")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    # Subcommands first.
    if getattr(args, "command", None) == "check":
        project_root = Path(args.project)
        cfg_path = Path(args.config)
        inputs_dir = None if args.inputs is None else Path(args.inputs)
        outdir = None if args.outdir is None else Path(args.outdir)

        result = run_check(
            project_root=project_root,
            config_path=cfg_path,
            inputs_dir=inputs_dir,
            outdir=outdir,
        )
        if result.has_errors:
            print("Check failed: errors found. See checks.md and staging_issues.csv")
            return 1
        print("Check passed (no errors).")
        return 0

    if getattr(args, "command", None) == "init":
        print("`ledgerloom init` is coming in PR06 (project skeleton).")
        return 2

    if getattr(args, "command", None) == "build":
        print("`ledgerloom build` is coming in PR07 (trusted pipeline run).")
        return 2

    if getattr(args, "command", None) == "report":
        print("`ledgerloom report` is a placeholder for future reporting UX.")
        return 2

    # Then top-level utility flags.
    if args.version:
        print(ledgerloom.__version__)
        return 0

    if args.paths:
        print(f"PROJECT_ROOT={ledgerloom.PROJECT_ROOT}")
        print(f"OUTPUTS_DIR={ledgerloom.OUTPUTS_DIR}")
        return 0

    if args.docs == "local":
        ledgerloom.open_local_docs()
        return 0
    if args.docs == "online":
        open_online_docs()
        return 0

    build_parser().print_help()
    return 0


def open_docs_cli() -> None:
    """Entry point for the `ledgerloom-docs` console script (opens local docs)."""
    ledgerloom.open_local_docs()

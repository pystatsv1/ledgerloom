from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import ledgerloom
from ledgerloom.docs_helper import open_online_docs
from ledgerloom.project.init import InitOptions, create_project_skeleton, default_period_today
from ledgerloom.project.check import run_check
from ledgerloom.project.suggest_mappings import run_suggest_mappings
from ledgerloom.project.build import BuildAbortError, run_build


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level LedgerLoom CLI parser.

    PR05 goal: present a product-style CLI with subcommands while preserving
    the existing --version flag behavior.

    Subcommands are intentionally minimal here. PR06 implements ``init``,
    PR04 implements ``check``, and PR07 implements ``build``.
    ``report`` remains a placeholder for later PRs.
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

    i = sub.add_parser("init", help="Create a new project skeleton")
    i.add_argument("path", help="Destination directory for the new project.")
    i.add_argument(
        "--name",
        default=None,
        help="Project display name (default: directory name).",
    )
    i.add_argument(
        "--period",
        default=None,
        help="Accounting period in YYYY-MM (default: current month).",
    )
    i.add_argument(
        "--currency",
        default="USD",
        help="Currency code (default: USD).",
    )

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
    b = sub.add_parser(
        "build",
        help="Create a run folder (snapshot + check + trust + postings + trial_balance + statements)",
    )
    b.add_argument(
        "--project",
        default=".",
        help="Project root directory (contains ledgerloom.yaml).",
    )
    b.add_argument(
        "--config",
        default="ledgerloom.yaml",
        help="Config file path (relative to --project unless absolute).",
    )
    b.add_argument(
        "--inputs",
        default=None,
        help="Override inputs directory (default: inputs/<period>/).",
    )
    b.add_argument(
        "--run-id",
        default=None,
        help="Run id (default: timestamp). Used as outputs/<run_id>/.",
    )
    b.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Disable copying inputs/configs into outputs/<run_id>/source_snapshot/.",
    )

    # Reporting UX placeholder (could later become report/open/run exports).
    s = sub.add_parser(
        "suggest-mappings",
        help="Generate YAML mapping rules from unmapped.csv (copy/paste helper)",
    )
    s.add_argument("--project", default=".", help="Project root directory")
    s.add_argument(
        "--config",
        default="ledgerloom.yaml",
        help="Project config path (relative to --project by default)",
    )
    s.add_argument(
        "--outdir",
        default=None,
        help="Check outdir containing unmapped.csv (defaults to outputs/check/<period>)",
    )
    s.add_argument(
        "--unmapped",
        default=None,
        help="Path to an unmapped.csv file (overrides --outdir)",
    )
    s.add_argument(
        "--out",
        default=None,
        help="Write YAML suggestions to a file (otherwise prints to stdout)",
    )

    sub.add_parser("report", help="Open or export reports for a run (future)")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    # Subcommands first.
    if getattr(args, "command", None) == "suggest-mappings":
        return run_suggest_mappings(
            project_root=Path(args.project),
            config_path=args.config,
            outdir=args.outdir,
            unmapped_path=args.unmapped,
            out_path=args.out,
        )

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
        dest = Path(args.path)
        project_name = args.name if args.name is not None else dest.name
        period = args.period if args.period is not None else default_period_today()
        currency = args.currency

        try:
            created = create_project_skeleton(
                dest,
                opts=InitOptions(project_name=project_name, period=period, currency=currency),
            )
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 2
        except FileExistsError as e:
            print(str(e), file=sys.stderr)
            return 1

        print(f"Created LedgerLoom project: {dest.resolve()}")
        for p in created:
            print(f"  - {p.as_posix()}")
        print("")
        print("Next:")
        print(f"  1) Put CSVs in inputs/{period}/")
        print("  2) Edit ledgerloom.yaml and config/chart_of_accounts.yaml")
        # Print a command that works regardless of the user's current directory.
        print(f"  3) Run: ledgerloom check --project {dest.as_posix()}")
        return 0

    if getattr(args, "command", None) == "build":
        project_root = Path(args.project)
        cfg_path = Path(args.config)
        inputs_dir = Path(args.inputs) if args.inputs is not None else None
        try:
            res = run_build(
                project_root=project_root,
                config_path=cfg_path,
                inputs_dir=inputs_dir,
                run_id=args.run_id,
                snapshot=not args.no_snapshot,
            )
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 2
        except FileExistsError as e:
            print(str(e), file=sys.stderr)
            return 1
        except BuildAbortError as e:
            print(str(e), file=sys.stderr)
            print(f"Run folder retained -> {e.run_root}", file=sys.stderr)
            if e.trust_outdir is not None:
                print(f"Wrote trust artifacts -> {e.trust_outdir}", file=sys.stderr)
            return 1

        print(f"Wrote run folder -> {res.run_root}")
        if not args.no_snapshot:
            print(f"Snapshotted sources -> {res.snapshot_root}")
        print(f"Wrote check artifacts -> {res.check_outdir}")
        print(f"Wrote trust artifacts -> {res.trust_outdir}")

        if res.check_result.has_errors:
            print(
                "Build stopped: check errors found (run folder retained). "
                "See checks.md and staging_issues.csv"
            )
            return 1

        postings = res.run_root / "artifacts" / "postings.csv"
        tb = res.run_root / "artifacts" / "trial_balance.csv"
        inc = res.run_root / "artifacts" / "income_statement.csv"
        bs = res.run_root / "artifacts" / "balance_sheet.csv"

        for p in (postings, tb, inc, bs):
            if p.exists():
                print(f"Wrote accounting artifact -> {p}")

        parts = ["snapshot", "check", "trust"]
        if postings.exists():
            parts.append("postings")
        if tb.exists():
            parts.append("trial_balance")
        if inc.exists() and bs.exists():
            parts.append("statements")
        print(f"Build OK ({' + '.join(parts)}). Next: closing entries.")
        return 0


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

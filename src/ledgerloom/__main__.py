from __future__ import annotations

import argparse

import ledgerloom
from ledgerloom.docs_helper import open_online_docs


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ledgerloom",
        description="LedgerLoom utilities (docs, paths, version).",
    )
    p.add_argument("--version", action="store_true", help="Print version and exit.")
    p.add_argument("--paths", action="store_true", help="Print important paths.")
    p.add_argument(
        "--docs",
        choices=["local", "online"],
        help="Open documentation (local requires `make docs`).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

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


if __name__ == "__main__":
    raise SystemExit(main())

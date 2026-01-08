from __future__ import annotations

import ledgerloom
from ledgerloom.cli import build_parser, main


def test_cli_help_shows_product_subcommands() -> None:
    help_text = build_parser().format_help()
    for cmd in ["init", "check", "build", "report"]:
        assert cmd in help_text
    assert "--version" in help_text


def test_cli_version_flag_prints_version(capsys) -> None:
    rc = main(["--version"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == ledgerloom.__version__

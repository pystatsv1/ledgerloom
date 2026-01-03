"""
DEPRECATED SHIM.

Chapter 01 runner moved into the installable package:

    python -m ledgerloom.chapters.ch01_journal_vs_eventlog ...

This shim keeps the old repo path working:

    python -m scripts.ledgerloom_ch01_journal_vs_eventlog ...
"""

from __future__ import annotations

from ledgerloom.chapters.ch01_journal_vs_eventlog import main


if __name__ == "__main__":
    raise SystemExit(main())
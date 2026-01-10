"""Ingestion adapters.

The ingest package bridges messy real-world input files (CSV exports from banks,
spreadsheets, etc.) into strict :class:`ledgerloom.core.Entry` objects.

In v0.2.x we ship:
- bank_feed.v1 (mapping-driven, two-leg entries)
- journal_entries.v1 (posting-line journal format; workbook unlock)
"""
from .csv_bank_feed import ingest_bank_feed_csv
from .csv_journal_entries import ingest_journal_entries_csv
from .models import BankFeedRule, BankFeedSourceConfig, IngestIssue, IngestResult

__all__ = [
    "BankFeedRule",
    "BankFeedSourceConfig",
    "IngestIssue",
    "IngestResult",
    "ingest_bank_feed_csv",
    "ingest_journal_entries_csv",
]

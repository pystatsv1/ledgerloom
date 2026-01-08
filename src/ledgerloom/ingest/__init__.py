"""Ingestion adapters.

The ingest package bridges messy real-world input files (CSV exports from banks,
payment providers, etc.) into strict :class:`ledgerloom.core.Entry` objects.

In v0.2.0 we start with a single adapter: bank feed CSV ingestion.
"""

from .csv_bank_feed import IngestResult, ingest_bank_feed_csv
from .models import BankFeedRule, BankFeedSourceConfig, IngestIssue

__all__ = [
    "BankFeedRule",
    "BankFeedSourceConfig",
    "IngestIssue",
    "IngestResult",
    "ingest_bank_feed_csv",
]

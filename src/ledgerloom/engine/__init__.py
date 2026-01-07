"""LedgerLoom Engine (v0.1).

This package contains reusable accounting primitives extracted from the
chapter runners. Chapters remain responsible for writing artifacts.

Public v0.1 API (intentionally small):
- :class:`ledgerloom.engine.config.LedgerEngineConfig`
- :class:`ledgerloom.engine.ledger.LedgerEngine`
- :class:`ledgerloom.engine.coa.COASchema`
"""

from .coa import Account, COASchema, SegmentValue
from .config import Dimension, LedgerEngineConfig
from .ledger import LedgerEngine

__all__ = [
    "Account",
    "SegmentValue",
    "COASchema",
    "Dimension",
    "LedgerEngineConfig",
    "LedgerEngine",
]

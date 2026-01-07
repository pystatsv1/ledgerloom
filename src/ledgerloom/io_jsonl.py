from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List

from .artifacts import write_jsonl as write_jsonl_dicts
from .core import Entry, Posting


def _encode_decimal(d: Decimal) -> str:
    return format(d, "f")


def write_jsonl(path: Path, entries: Iterable[Entry]) -> None:
    """Write entries to JSONL with stable ordering and LF line endings."""

    def rows() -> Iterable[dict[str, object]]:
        for e in entries:
            yield {
                "dt": e.dt.isoformat(),
                "narration": e.narration,
                "postings": [
                    {"account": p.account, "debit": _encode_decimal(p.debit), "credit": _encode_decimal(p.credit)}
                    for p in e.postings
                ],
                "meta": e.meta,
            }

    # Delegate the byte-level details (newline handling, compact JSON) to artifacts.
    write_jsonl_dicts(path, rows(), sort_keys=True, ensure_ascii=False)


def read_jsonl(path: Path) -> List[Entry]:
    entries: List[Entry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        entries.append(
            Entry(
                dt=date.fromisoformat(obj["dt"]),
                narration=obj["narration"],
                postings=[
                    Posting(
                        account=p["account"],
                        debit=Decimal(p["debit"]),
                        credit=Decimal(p["credit"]),
                    )
                    for p in obj["postings"]
                ],
                meta=obj.get("meta", {}),
            )
        )
    return entries

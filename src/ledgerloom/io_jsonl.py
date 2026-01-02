from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List

from .core import Entry, Posting


def _encode_decimal(d: Decimal) -> str:
    return format(d, "f")


def write_jsonl(path: Path, entries: Iterable[Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            obj = {
                "dt": e.dt.isoformat(),
                "narration": e.narration,
                "postings": [
                    {"account": p.account, "debit": _encode_decimal(p.debit), "credit": _encode_decimal(p.credit)}
                    for p in e.postings
                ],
                "meta": e.meta,
            }
            f.write(json.dumps(obj) + "\n")


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

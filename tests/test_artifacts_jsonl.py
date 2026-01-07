from __future__ import annotations

from pathlib import Path

from ledgerloom.artifacts import write_jsonl


def test_write_jsonl_is_deterministic_and_uses_lf(tmp_path: Path) -> None:
    p = tmp_path / "demo.jsonl"
    write_jsonl(p, [{"b": 2, "a": 1}, {"a": "hi"}])

    raw = p.read_bytes()
    # Cross-platform stability: no CRLF translation.
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")

    assert raw == b"{\"a\":1,\"b\":2}\n{\"a\":\"hi\"}\n"

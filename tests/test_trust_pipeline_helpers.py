from __future__ import annotations

import json
from pathlib import Path

from ledgerloom.artifacts import (
    MANIFEST_SCHEMA_V1,
    RUN_META_SCHEMA_V1,
    artifacts_map,
    manifest_items_prefixed,
    sha256_bytes,
    specs_with_hashes,
    write_manifest,
    write_run_meta,
)


def test_write_manifest_injects_schema_and_uses_lf(tmp_path: Path) -> None:
    p = tmp_path / "manifest.json"
    write_manifest(p, {"artifacts": []})

    raw = p.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")

    obj = json.loads(raw.decode("utf-8"))
    assert obj["schema"] == MANIFEST_SCHEMA_V1
    assert obj["artifacts"] == []


def test_write_run_meta_injects_schema_and_uses_lf(tmp_path: Path) -> None:
    p = tmp_path / "run_meta.json"
    write_run_meta(p, {"chapter": "ch00", "seed": 123})

    raw = p.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")

    obj = json.loads(raw.decode("utf-8"))
    assert obj["schema"] == RUN_META_SCHEMA_V1
    assert obj["chapter"] == "ch00"


def test_artifacts_map_hashes_and_sizes(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8", newline="\n")
    (tmp_path / "b.bin").write_bytes(b"\x00\x01\x02")

    m = artifacts_map(tmp_path, ["a.txt", "b.bin"])

    assert m["a.txt"]["bytes"] == 6
    assert m["a.txt"]["sha256"] == sha256_bytes(b"hello\n")

    assert m["b.bin"]["bytes"] == 3
    assert m["b.bin"]["sha256"] == sha256_bytes(b"\x00\x01\x02")


def test_manifest_items_prefixed_records_prefixed_paths(tmp_path: Path) -> None:
    (tmp_path / "x.csv").write_text("a,b\n1,2\n", encoding="utf-8", newline="\n")

    items = manifest_items_prefixed(tmp_path, ["x.csv"], prefix="ch085", name_key="path")
    assert items[0]["path"] == "ch085/x.csv"
    assert items[0]["bytes"] == 8


def test_specs_with_hashes_augments_specs(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    specs = [{"name": "a.txt", "description": "A file"}]

    out = specs_with_hashes(tmp_path, specs)
    assert out[0]["name"] == "a.txt"
    assert out[0]["description"] == "A file"
    assert out[0]["bytes"] == 5
    assert out[0]["sha256"] == sha256_bytes(b"hello")

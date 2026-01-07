from __future__ import annotations

import json
from pathlib import Path

from ledgerloom.trust.pipeline import emit_trust_artifacts


def test_emit_trust_artifacts_injects_schema_and_is_deterministic(tmp_path: Path) -> None:
    outdir = tmp_path / "chXX"
    outdir.mkdir(parents=True, exist_ok=True)

    run_meta = {
        "chapter": "XX",
        "seed": 123,
        "note": "payload is opaque to pipeline; writers are deterministic",
    }
    manifest = {
        "chapter": "XX",
        "artifacts": [
            {
                "name": "example.txt",
                "bytes": 3,
                "sha256": "0" * 64,
            }
        ],
    }

    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=manifest)

    rm_path = outdir / "run_meta.json"
    mf_path = outdir / "manifest.json"
    assert rm_path.exists()
    assert mf_path.exists()

    rm = json.loads(rm_path.read_text(encoding="utf-8"))
    mf = json.loads(mf_path.read_text(encoding="utf-8"))

    assert rm["schema"] == "ledgerloom.run_meta.v1"
    assert mf["schema"] == "ledgerloom.manifest.v1"

    # LF trailing newline contract.
    assert rm_path.read_bytes().endswith(b"\n")
    assert mf_path.read_bytes().endswith(b"\n")

    # Determinism: same payloads -> byte-identical files.
    rm_bytes_1 = rm_path.read_bytes()
    mf_bytes_1 = mf_path.read_bytes()
    emit_trust_artifacts(outdir, run_meta=run_meta, manifest=manifest)
    assert rm_path.read_bytes() == rm_bytes_1
    assert mf_path.read_bytes() == mf_bytes_1

"""Trust pipeline utilities.

The trust pipeline exists to make chapter artifacts:

* deterministic (byte-stable across platforms)
* verifiable (hashed + described)
* schema-tagged (explicit versioned contracts)

Chapters still decide *what* to write; this package centralizes *how* the
reproducibility artifacts are emitted.
"""

from __future__ import annotations

__all__ = [
    "emit_trust_artifacts",
    "manifest_artifacts_from_specs",
    "run_meta_artifacts_from_names",
]

from .pipeline import (  # noqa: E402
    emit_trust_artifacts,
    manifest_artifacts_from_specs,
    run_meta_artifacts_from_names,
)

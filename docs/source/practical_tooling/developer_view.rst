Developer view (contracts + trust)
==================================

LedgerLoom is intentionally “boring” software: deterministic I/O, explicit schemas, and artifacts
you can hash and verify.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** LedgerLoom’s “trust” folder is the audit trail of how the outputs were produced.

   **Developer:** The manifest hash is your content-addressed build ID.

   **Data pro:** Deterministic artifacts mean your analyses are reproducible and comparable across runs.

Core contracts
--------------

Project root contract
~~~~~~~~~~~~~~~~~~~~~

A build/check always starts from a **project root** containing ``ledgerloom.yaml``.
Everything else (inputs, outputs, COA, mappings) is resolved relative to that root.

Determinism contract
~~~~~~~~~~~~~~~~~~~~

Given the same:

- project config
- inputs
- mapping rules
- engine version

LedgerLoom aims to produce identical bytes for the trust manifest.

Trust model
-----------

A successful ``ledgerloom build`` writes:

- ``trust/manifest.json`` — the content-addressed manifest of run artifacts
- ``trust/run_meta.json`` — metadata for the run (including ``run_id``)

The intent is that you can:

- store manifests in CI artifacts
- compare manifest hashes between runs
- diff the manifest payload to see what changed

CI smoke tests
--------------

The repo includes smoke tests that:

- build a real example project in ``examples/real_world_scenario``
- build twice
- assert the manifest hashes match (determinism)

This is the “proof” that LedgerLoom is safe to automate.

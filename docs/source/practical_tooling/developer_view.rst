Developer view
==============

This page explains the **contracts** behind the practical tool, so you can extend LedgerLoom
confidently (new sources, new validations, new reports) without breaking determinism.

Project as config (no Python required)
--------------------------------------

A LedgerLoom project is defined by a single YAML file:

- ``ledgerloom.yaml`` — validated by ``ledgerloom.project.config.ProjectConfig``

The config points to:

- a chart of accounts YAML (COA)
- one or more sources (bank feed v1 for now)
- optional mapping rules (regex → account)
- build behavior flags (e.g., ``strict_unmapped`` and ``suspense_account``)

The practical tool contract is: **same inputs + same config ⇒ same outputs** (byte-stable).

Run folder contract
-------------------

``ledgerloom build`` writes a *run directory* under ``outputs/<run_id>/`` with four subfolders:

- ``source_snapshot/`` — copies of project config + the input files used for the run
- ``check/`` — the gatekeeper outputs from ``ledgerloom check`` (staging + issues + unmapped)
- ``artifacts/`` — accounting outputs (postings + trial balance + statements, and reclass helpers)
- ``trust/`` — ``run_meta.json`` + ``manifest.json`` (hashes for all tracked files)

The folder structure is intentionally simple so it can be versioned and inspected in Git,
archived, or attached to a ticket/email.

Data contracts: entries → postings
----------------------------------

The ingestion layer emits **Entry** objects (double-entry journal records). The build pipeline
derives a postings table using the engine:

- Entries are posted via ``LedgerEngine.postings_fact_table(entries)``
- The postings table is then used to derive trial balance and statements

Key stability guarantees:

- Entries include a deterministic ``meta["entry_id"]`` (stable across runs for the same input row)
- Postings are sorted deterministically (stable sort on ``date``, ``entry_id``, ``line_no``)

Trust model: manifest + deterministic hashing
---------------------------------------------

LedgerLoom's trust model is **content-addressed**:

- ``trust/manifest.json`` records *all tracked files* and their SHA-256 hashes
- ``trust/run_meta.json`` records run metadata (including ``run_id``)

Important: ``run_id`` is **not** part of the manifest payload. This ensures the manifest hash
is a stable trust anchor for idempotency checks.

Determinism / idempotency check
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Two builds over the same inputs/config should produce the same manifest hash:

.. code-block:: bash

   ledgerloom build --project examples/real_world_scenario --run-id run-a
   ledgerloom build --project examples/real_world_scenario --run-id run-b

   sha256sum examples/real_world_scenario/outputs/run-a/trust/manifest.json \
            examples/real_world_scenario/outputs/run-b/trust/manifest.json

If these differ, treat it as a **bug**: it means file ordering, serialization, or parsing is
no longer strictly deterministic.

Exception workflow (suspense + reclass)
---------------------------------------

Real books are messy. LedgerLoom keeps the pipeline moving by default:

- if a staged row does not match any mapping rule, it is posted to ``suspense_account``
- unmapped rows are written to ``artifacts/unmapped.csv``
- a helper ``artifacts/reclass_template.csv`` is written to guide reclass entries

When you are ready to enforce strictness, set:

- ``strict_unmapped: true``

Then builds with unmapped rows raise ``BuildAbortError`` (after writing the run folder + trust files),
so you can fix mappings before publishing results.

Extension points (where to add features)
----------------------------------------

If you want to extend LedgerLoom, keep these seams in mind:

- **New sources:** add an ingest adapter under ``ledgerloom.ingest`` and map it from config.
- **New validations:** add checks in ``ledgerloom.project.check`` (emit machine-readable issues).
- **New artifacts:** write a stable table under ``artifacts/`` and include it in the manifest.
- **New schemas:** keep file schemas versioned and documented (CSV headers are part of the contract).

The north star is: additions are easy, but contracts remain stable.

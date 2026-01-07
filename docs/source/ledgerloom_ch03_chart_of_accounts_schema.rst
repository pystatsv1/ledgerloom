Chapter 03: Chart of Accounts as Schema
=======================================

This is an *alternate* Chapter 03 (for now).

- :doc:`ledgerloom_ch03_posting_to_ledger` shows how a **journal** becomes a **ledger** + **trial balance**.
- This chapter treats the **Chart of Accounts (COA)** as a **schema**: metadata + constraints + join keys.

If you’ve ever wished your accounting exports were as well-defined as a database table or an API contract,
this chapter is for you.

What you will build
-------------------

1) A COA schema (metadata + constraints)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You’ll define a **schema** for account master records:

- account type (asset/liability/equity/revenue/expense)
- normal balance side (debit/credit)
- statement mapping (BS vs IS)
- rollups (hierarchical reporting)
- segment flags (department/project tracking)

2) An “account master” table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You’ll generate an **account master** CSV that is designed for:

- joins (ledger ↔ accounts ↔ statements)
- validation (uniqueness, rollups, conventions)
- contributor friendliness (clear columns, stable ordering)
- determinism (golden-file tests)

Why this matters
----------------

In real life, the COA is often stored in a spreadsheet or a legacy ERP menu.
But for modern analytics + automation, we want the COA to be:

- **Queryable** (a table with stable keys)
- **Validated** (constraints + invariants)
- **Composable** (rollups + metadata)
- **Reproducible** (deterministic outputs + hashes)

LedgerLoom treats the COA like a schema contract that future chapters will build on.

Run the chapter
---------------

From the repo root:

.. code-block:: bash

   python -m ledgerloom.chapters.ch03_chart_of_accounts_schema --outdir outputs/ledgerloom --seed 123

Or via Makefile:

.. code-block:: bash

   make ll-ch03-coa
   # (alias)
   make ll-ch03AccountsSchema

Artifacts are written under:

.. code-block:: text

   outputs/ledgerloom/ch03AccountsSchema/

Artifacts
----------------------------

Core schema + tables
^^^^^^^^^^^^^^^^^^^^

- ``coa_schema.json``
  Schema definition (fields + constraints + segment metadata).

- ``account_master.csv``
  The account master table (the join backbone of the system).

- ``segment_dimensions.csv`` + ``segment_values.csv``
  A minimal segment “dictionary” (Department + Project).

Worked example
^^^^^^^^^^^^^^

- ``income_statement_by_department.csv``
  A tiny *statement by segment* example to show why segments matter.

WOW / developer artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^

- ``checks.md``
  Invariant checks: uniqueness, rollup validity, mapping conventions.

- ``tables.md``
  Quick Markdown tables so you can inspect the COA instantly.

- ``diagnostics.md``
  Canonical hashes and design notes (helps contributors trust the pipeline).

- ``lineage.mmd``
  Mermaid lineage diagram of artifact dependencies.

- ``manifest.json``
  Inventory of artifacts with byte counts and sha256 hashes.

- ``run_meta.json``
  Run metadata (seed + module name).

- ``summary.md``
  One-page “what you built” recap.

How to read the outputs
-----------------------

Start here:

1) ``tables.md`` — instant tour of the COA + segments + example statement
2) ``account_master.csv`` — the join backbone (codes, types, rollups, segment flags)
3) ``coa_schema.json`` — the contract / constraints
4) ``checks.md`` — the invariants you can trust

Exercises (good first contributions)
------------------------------------

- Add one new account (e.g., ``1350 Prepaid Expenses``) and update rollups.
- Add one new department segment value (e.g., ``FIN Finance``).
- Extend the schema with an ``effective_date`` field to demonstrate versioning.
- Add a new golden-file for a new output (determinism is a feature).

Notes for contributors
----------------------

This chapter is intentionally “schema-first”. Later chapters can rely on the COA as:

- a validated table for joins
- a source of truth for statement mapping
- metadata for segment reporting

Golden-file tests enforce determinism. If you change outputs on purpose,
update the corresponding golden files in ``tests/golden/ch03AccountsSchema/``.

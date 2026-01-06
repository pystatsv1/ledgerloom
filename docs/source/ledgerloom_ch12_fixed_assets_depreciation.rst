LedgerLoom Chapter 12 — Fixed assets and depreciation
=====================================================

This chapter introduces **fixed assets** (capitalization vs expense) and builds
a tiny **depreciation engine** that emits monthly journal entries.

What you build
--------------

* A small *capitalization policy* (threshold-based) that classifies purchases as:

  * **capitalize** → record a fixed asset (balance sheet)
  * **expense** → record a period cost (income statement)

* A deterministic **straight-line** depreciation schedule generator
* A monthly **depreciation event stream**:

  ``Dr Expenses:Depreciation``

  ``Cr Assets:FixedAssets:AccumulatedDepreciation``

* A disposal example (remove cost + accumulated depreciation; recognize gain/loss)
* A simple control reconciliation: subledger net fixed assets equals the G/L net

How to run
----------

.. code-block:: console

   make ll-ch12

Artifacts
---------

The Chapter 12 runner writes ``outputs/ledgerloom/ch12`` containing:

* ``capitalization_decisions.csv`` — purchase classification (capitalize vs expense)
* ``fixed_assets_register.csv`` — asset master data (cost, life, disposal)
* ``depreciation_schedule.csv`` — per-asset monthly schedule (amount, accum, NBV)
* ``depreciation_events.csv`` — the monthly depreciation journal events
* ``fixed_assets_control_reconciliation.csv`` — subledger vs G/L net fixed assets
* Standard LedgerLoom artifacts: postings, trial balance, statements, invariants, manifest

Notes and limitations
---------------------

This is a **teaching implementation**:

* Straight-line only (no MACRS, double-declining, component depreciation)
* No partial-month conventions (the example treats the in-service month as a full month)
* Accumulated depreciation is modeled as a contra-asset account under ``Assets``
  (it naturally carries a negative balance)

These constraints keep the model small, deterministic, and testable.

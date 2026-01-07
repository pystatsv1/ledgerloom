LedgerLoom Chapter 11 — Inventory and COGS
==========================================

This chapter introduces **inventory** as an operational subsystem and shows how to
link **inventory movements** to **Cost of Goods Sold (COGS)**.

What you build
--------------

* A tiny, deterministic inventory movement stream:

  * purchase receipts (inventory increases)
  * sales issues (inventory decreases; COGS increases)
  * shrink adjustment (cycle count / loss)

* A **moving-average** perpetual costing model (simple on purpose)
* A subledger valuation (units + cost) and a **control reconciliation**:

  ``Assets:Inventory (G/L)`` equals ``inventory valuation (subledger)``

How to run
----------

.. code-block:: console

   make ll-ch11

Artifacts
---------

The Chapter 11 runner writes ``outputs/ledgerloom/ch11`` containing:

* ``inventory_movements.csv`` — movement register with computed unit costs
* ``sales_register.csv`` — sales with revenue amounts
* ``cogs_by_sale.csv`` — per-sale COGS linkage
* ``inventory_valuation_end_period.csv`` — ending on-hand + valuation
* ``inventory_control_reconciliation.csv`` — subledger vs G/L control
* Standard LedgerLoom artifacts: postings, trial balance, statements, invariants, manifest

Notes and limitations
---------------------

This is a **teaching implementation**:

* Single SKU (easy to extend by keying state per SKU)
* Moving-average cost (no FIFO/LIFO layers, no lot tracking)
* No returns or backdated receipts in the minimal dataset

These constraints keep the model small, deterministic, and testable — and make
the limitations explicit for students.

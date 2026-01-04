LedgerLoom Chapter 02 — Debits/Credits encoding (wide vs long)
=============================================================

Status
------

**Implemented (demo runner + artifacts).**

What this chapter is about
--------------------------

In the wild, accounting data shows up in different shapes depending on the source system.

Two common encodings:

* **Wide encoding** (one row per transaction): explicit debit-side and credit-side columns.
* **Long encoding** (two+ rows per transaction): one row per posting, with a ``side`` column.

LedgerLoom treats these as *different representations of the same facts*.
The goal of this chapter is to show that both encodings can compile into the same
canonical journal (entries + postings) and therefore produce identical financial reports.

How to run it
-------------

From the repo root:

.. code-block:: bash

   # Run via Makefile (recommended)
   make ll-ch02

   # Or run the module directly
   python -m ledgerloom.chapters.ch02_debits_credits_encoding --outdir outputs/ledgerloom --seed 123

Outputs
-------

The runner writes a small set of artifacts under:

``outputs/ledgerloom/ch02/``

* ``encoding_wide.csv`` — example transactions in wide debit/credit form
* ``encoding_long.csv`` — the same transactions in long form (one row per posting)
* ``journal_from_wide.jsonl`` — compiled canonical entries from the wide table
* ``journal_from_long.jsonl`` — compiled canonical entries from the long table
* ``trial_balance.csv`` — trial balance from the compiled journal
* ``income_statement.csv`` — income statement from the compiled journal
* ``balance_sheet.csv`` — balance sheet from the compiled journal
* ``run_meta.json`` — lightweight metadata for reproducibility
* ``summary.md`` — a short human-readable summary

Key result
----------

The demo is designed so that these two outputs are byte-for-byte identical:

* ``journal_from_wide.jsonl``
* ``journal_from_long.jsonl``

That determinism makes it easy to test and easy to reason about transformations.

Next up
-------

Chapter 03 introduces a Chart of Accounts schema, so we can validate account naming,
typing, and reporting structure.

LedgerLoom Chapter 02 — Debits/Credits encoding (wide, long, signed)
===================================================================

Status
------

**Implemented (demo runner + artifacts).**

What this chapter is about
--------------------------

In the wild, accounting data shows up in different shapes depending on the source system.

Three common encodings:

* **Wide encoding** (one row per transaction): explicit debit-side and credit-side columns.
* **Long encoding** (two+ rows per transaction): one row per posting, with a ``side`` column.
* **Signed encoding** (two+ rows per transaction): one row per posting, with a single signed amount column.

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
* ``encoding_signed.csv`` — the same transactions in a modern signed form (debits positive, credits negative)
* ``journal_from_wide.jsonl`` — compiled canonical entries from the wide table
* ``journal_from_long.jsonl`` — compiled canonical entries from the long table
* ``journal_from_signed.jsonl`` — compiled canonical entries from the signed table
* ``diagnostics.md`` — invariants + equivalence checks (hashes)
* ``trial_balance.csv`` — trial balance from the compiled journal
* ``income_statement.csv`` — income statement from the compiled journal
* ``balance_sheet.csv`` — balance sheet from the compiled journal
* ``run_meta.json`` — lightweight metadata for reproducibility
* ``summary.md`` — a short human-readable summary

Key result
----------

The demo is designed so that these three outputs are byte-for-byte identical:

* ``journal_from_wide.jsonl``
* ``journal_from_long.jsonl``
* ``journal_from_signed.jsonl``

That determinism makes it easy to test and easy to reason about transformations.

Signed encoding note
-------------------

The signed encoding used here is intentionally **journal-centric** (not account-type aware):

* debit postings are positive
* credit postings are negative

The *accounting* comes from invariants (sum to 0 per transaction, balanced entries, correct rollups),
not from the presence of two separate columns.

Next up
-------

Chapter 03 introduces a Chart of Accounts schema, so we can validate account naming,
typing, and reporting structure.

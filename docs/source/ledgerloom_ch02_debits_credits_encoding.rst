Chapter 02 — Debits & Credits as Encodings (Wide, Long, Signed)
===============================================================

Chapter 01 introduced the idea that accounting can be represented as a **canonical journal**
(entries + postings) and then reported in consistent ways (trial balance, income statement,
balance sheet).

This chapter takes the next step:

**The same accounting facts can be stored in different table shapes — and still compile into the
exact same canonical journal.**

In other words: *accounting is defined by invariants, not by column names.*

What you will build
-------------------

You will generate a tiny, meaningful demo dataset and produce:

Three encodings of the same transactions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Wide**: one row per transaction with explicit debit/credit columns
- **Long**: many rows per transaction with a ``side`` column (debit/credit)
- **Signed**: many rows per transaction with a single ``signed_amount`` column

A canonical journal
^^^^^^^^^^^^^^^^^^^

From each encoding we compile **the same** canonical journal:

- ``journal_from_wide.jsonl``
- ``journal_from_long.jsonl``
- ``journal_from_signed.jsonl``

Reports from the journal
^^^^^^^^^^^^^^^^^^^^^^^^

- ``trial_balance.csv``
- ``income_statement.csv``
- ``balance_sheet.csv``

Proof + "wow" artifacts
^^^^^^^^^^^^^^^^^^^^^^^

- ``checks.md`` — PASS/FAIL invariant checks
- ``diagnostics.md`` — narrative explanation + hashes
- ``tables.md`` — the encodings and reports as readable Markdown tables
- ``lineage.mmd`` — Mermaid lineage diagram (encodings → journal → reports)
- ``manifest.json`` / ``run_meta.json`` — reproducibility metadata + hashes

The core idea: facts vs encoding
--------------------------------

A transaction like:

- Debit ``Assets:Cash`` $5000
- Credit ``Equity:OwnerCapital`` $5000

is a *fact*.

How you store that fact in a table is an *encoding choice*.

LedgerLoom treats the encoding as input, compiles it into canonical journal entries, and then
enforces accounting correctness through invariants.

Encoding 1: wide (classic debit/credit columns)
-----------------------------------------------

The wide encoding is common in exports:

- one row per transaction
- two posting columns: debit side and credit side

Columns in ``encoding_wide.csv`` include:

- ``tx_id`` — transaction id (groups postings)
- ``dt`` — ISO date
- ``narration`` — description
- ``debit_account``, ``debit_amount``
- ``credit_account``, ``credit_amount``

This is extremely readable for humans, but it is not always the best shape for analytics
(because debits and credits are split across columns).

Encoding 2: long (one posting per row)
--------------------------------------

The long encoding is common in databases and analytics pipelines:

- one row per posting
- a ``side`` column indicates debit vs credit

Columns in ``encoding_long.csv`` include:

- ``tx_id``, ``dt``, ``narration``
- ``side`` — ``debit`` or ``credit``
- ``account``
- ``amount``

This is more "relational" and is easy to group, filter, and join.

Encoding 3: signed (single numeric measure)
-------------------------------------------

The signed encoding is a long table where the numeric measure carries direction:

- debits are positive
- credits are negative

Columns in ``encoding_signed.csv`` include:

- ``tx_id``, ``dt``, ``narration``
- ``account``
- ``signed_amount``

Why this is powerful:

- you can aggregate with *one* numeric column
- you can build models on postings without pivot/unpivot steps
- correctness is enforced by invariants (the sum of ``signed_amount`` must be zero per transaction)

Compiling encodings into the canonical journal
----------------------------------------------

Each encoding is compiled into a list of ``Entry`` objects, each containing a date,
narration, and a list of ``Posting`` objects.

The canonical journal is written as deterministic JSONL so you can diff it, hash it,
and treat it like a proper artifact.

Key point:

**All three compiled journals are byte-identical.**

That is the chapter's "proof of equivalence".

Invariants (the accounting "safety rails")
------------------------------------------

LedgerLoom enforces the invariants that make double-entry bookkeeping work:

- Each transaction balances (total debits == total credits)
- In signed form: each transaction sums to zero (sum(signed_amount) == 0)
- Trial balance is consistent with the journal
- Financial statements are consistent with the trial balance

These invariants are captured for humans in:

- ``checks.md`` (PASS/FAIL)
- ``diagnostics.md`` (hashes + explanation)

and for machines in:

- ``run_meta.json`` / ``manifest.json``

How to run
----------

From the repo root:

.. code-block:: bash

   # Run Chapter 02 demo (writes into outputs/ledgerloom/ch02)
   python -m ledgerloom.chapters.ch02_debits_credits_encoding --outdir outputs/ledgerloom --seed 123

Or using the Makefile target (if available):

.. code-block:: bash

   make ll-ch02

Where to look after running:

.. code-block:: text

   outputs/ledgerloom/ch02/
     encoding_wide.csv
     encoding_long.csv
     encoding_signed.csv
     journal_from_wide.jsonl
     journal_from_long.jsonl
     journal_from_signed.jsonl
     trial_balance.csv
     income_statement.csv
     balance_sheet.csv
     checks.md
     diagnostics.md
     tables.md
     lineage.mmd
     manifest.json
     run_meta.json
     summary.md

Recommended reading order
-------------------------

If you want the fastest "wow":

1. Open ``summary.md`` (high-level tour)
2. Open ``tables.md`` (see the data)
3. Open ``checks.md`` (PASS/FAIL invariants)
4. Open ``diagnostics.md`` (hashes + reasoning)
5. Open ``manifest.json`` (artifact hashes + sizes)

Exercises
---------

1. **Add a new transaction**
   - Add a new wide row in the chapter script demo dataset.
   - Regenerate outputs and verify all checks still PASS.

2. **Create a multi-posting transaction**
   - Extend the demo so that one transaction has *three* postings.
   - Hint: wide encoding becomes awkward; long and signed remain natural.

3. **Stress-test your intuition**
   - Change only the ordering of rows in ``encoding_long.csv`` and rerun.
   - The canonical journal should remain identical (stable grouping rules).

Developer notes
---------------

- This chapter deliberately keeps the demo dataset small enough to read in one sitting.
- Outputs are deterministic for a fixed seed to keep tests stable and diffs meaningful.
- The canonical journal and reports are the "source of truth"; encodings are just views.

Next
----

Chapter 03 will introduce a Chart of Accounts schema so that account strings can be validated
(and later, used for roll-ups and richer reporting).

Chapter 05 — Accounting equation as an invariant
===================================================

In Chapters 01–04 we built the core idea of a ledger:

- **Journal entries** are structured events
- An **append-only event log** is the source of truth
- The **general ledger** is a database you can query
- The **double-entry invariant** holds per entry (debits = credits)

This chapter adds a second, equally important invariant:

- The ledger is balanced *in aggregate* in a way that preserves the **accounting equation**.

Why this matters
----------------

A ledger can be “double-entry correct” (each entry balances) but still produce nonsense financials if:

- accounts are mis-classified (Asset posted to Revenue, etc.)
- a chart of accounts mixes incompatible roots (Income vs Revenue, etc.)
- reports use inconsistent sign conventions

The accounting equation is a structural check that your schema + postings make sense together.

Expanded equation (because we keep Revenue/Expenses open)
---------------------------------------------------------

LedgerLoom keeps temporary accounts (Revenue/Expenses) open through these early chapters, so we use the expanded form:

.. code-block:: text

   Assets = Liabilities + Equity + Revenue - Expenses

This is equivalent to a “sum-to-zero” check if you compute **raw balances** as:

.. code-block:: text

   raw_delta = debit - credit    # debit-positive, credit-negative

Then:

.. code-block:: text

   Assets + Liabilities + Equity + Revenue + Expenses == 0

What you will build
-------------------

- A **postings fact table** (``postings.csv``) — the same core table used in Chapter 04
- A derived view (``equation_check_by_entry.csv``) that shows **running balances** and the equation **diff** after each entry
- ``invariants.json`` that includes engine invariants plus an **accounting equation check**
- ``manifest.json`` to make artifacts content-addressable (sha256 + size)

Run it
------

.. code-block:: bash

   make ll-ch05

Outputs are written to:

.. code-block:: text

   outputs/ledgerloom/ch05/

Artifacts
---------

- ``postings.csv``
  - The ledger “fact table” (one row per posting).
- ``equation_check_by_entry.csv``
  - Running totals by root (Assets/Liabilities/Equity/Revenue/Expenses) and:

    - ``rhs_liab_plus_equity_plus_rev_minus_exp``
    - ``diff_assets_minus_rhs`` (must be ``0.00``)
- ``invariants.json``
  - Engine checks + ``accounting_equation_ok`` and any failing entry ids.
- ``manifest.json``
  - sha256 + byte size for each artifact.

Implementation notes
--------------------

- **Double-entry** is checked per entry via the postings table (Chapter 04).
- The **equation** is checked across cumulative balances by root.
- This chapter intentionally uses a **small dataset** that touches every root,
  so you can see the equation stabilize as the business evolves.

Next steps
----------

If Chapter 05 is green and the docs read well, we can push on to Chapter 06
and start building more “real business” transactions while keeping these invariants enforced.

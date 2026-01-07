LedgerLoom Chapter 07 — Adjusting entries as “late-arriving data”
=================================================================

Chapter 06 introduced *periods* and the idea that **timing** changes what “profit” means.
Chapter 07 makes that operational: it shows how real closes work when information arrives
*after* period end.

In accounting language, these are **adjusting entries** (accruals, deferrals, estimates).
In software language, they are **late-arriving events** that we ingest *after* the period
boundary.

The key engineering principle:
**Never overwrite history.** Append new events, record provenance, and rebuild derived views.

Why this matters (accountants + engineers + data people)
--------------------------------------------------------

*Accountants* get:
- a clean “unadjusted” close vs. an “adjusted” close
- a documented audit trail for who posted what and why
- repeatable evidence that the trial balance and equation still hold

*Software developers* get:
- an event-sourced model: adjustments are separate events
- deterministic compilation: same inputs → same postings → same reports
- testable invariants as constraints (double-entry + equation)

*Data professionals* get:
- a reproducible pipeline: append-only facts + derived views
- explicit handling of late data (cutoff diagnostics)
- stable artifacts for downstream analysis and monitoring

What you will build
-------------------

This chapter emits **two** close snapshots for the same period:

1) **Unadjusted** close: what was recorded by the deadline.
2) **Adjusted** close: unadjusted + adjusting entries dated at period end, with provenance.

The example adjustments include:

- Deferring unearned revenue (customer prepayment)
- Reclassifying prepaid rent
- Accruing a utility bill received after month-end
- Recognizing supplies used based on a month-end count

Outputs (artifacts)
-------------------

The runner writes artifacts under ``outputs/ledgerloom/ch07``:

- ``postings_unadjusted.csv`` and ``postings_adjusted.csv``
- ``trial_balance_unadjusted.csv`` and ``trial_balance_adjusted.csv``
- ``income_statement_unadjusted.csv`` and ``income_statement_adjusted.csv``
- ``balance_sheet_unadjusted.csv`` and ``balance_sheet_adjusted.csv``
- ``entry_register.csv`` (all events) and ``adjustments_register.csv`` (adjustments only)
- ``cutoff_audit.csv`` (late-arrival diagnostics: effective period vs posted period)
- ``adjustment_deltas_by_account.csv`` (what changed, by account)
- ``invariants.json`` (engine invariants for both snapshots + equation checks)
- ``manifest.json`` (run metadata + SHA256 checksums)

Run it
------

.. code-block:: bash

   make ll-ch07

Or directly:

.. code-block:: bash

   python -m ledgerloom.chapters.ch07_adjusting_entries_late_arriving_data \
     --outdir outputs/ledgerloom \
     --seed 123

How to read the outputs
-----------------------

Start with these three files:

1) ``trial_balance_unadjusted.csv`` vs ``trial_balance_adjusted.csv``
   shows the *account-level* impact of the adjustments.

2) ``income_statement_*`` shows how timing changes profit.

3) ``cutoff_audit.csv`` explains *why* the adjustments exist:
   the entry effective date is period-end, but the ``posted_at`` date is later.

Engineering takeaway: append-only + provenance + deterministic rebuild
----------------------------------------------------------------------

LedgerLoom treats adjustments as first-class events. That lets you:

- reproduce any close (unadjusted or adjusted) from the event log
- audit “who/why/when/source” without guessing
- enforce constraints with tests, not tribal knowledge

This is the same workflow you want in production accounting software:
**trust comes from invariants, provenance, and reproducibility.**

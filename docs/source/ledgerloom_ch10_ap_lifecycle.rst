LedgerLoom Chapter 10 — Accounts Payable Lifecycle
==================================================

This chapter introduces **Accounts Payable (A/P)** as a **control account + subledger** pattern.

What you build
--------------

* An opening balance carry-forward entry (same continuity idea as Chapter 08.5)
* A tiny A/P operational flow:

  * vendor bills (A/P increases)
  * vendor credit memo (A/P decreases; reverses expense)
  * vendor payments (A/P decreases; cash decreases)

* An **open-items** subledger with aging buckets
* A control reconciliation: ``A/P control (G/L)`` equals ``sum(open items)``

How to run
----------

.. code-block:: console

   make ll-ch10

Artifacts
---------

The chapter writes deterministic learning artifacts into ``outputs/ledgerloom/ch10``:

* ``vendor_bills_register.csv``
* ``vendor_credits_register.csv``
* ``cash_disbursements_register.csv``
* ``ap_open_items.csv`` (open items + aging)
* ``ap_control_reconciliation.csv``

Plus continuity artifacts (post-close snapshot, opening entry, reconciliation) and standard reports:

* ``trial_balance_end_period.csv``
* ``income_statement_current_period.csv``
* ``balance_sheet_current_period.csv``

Teachable checks
----------------

One bill is **intentionally left unapproved** so you can see how a checklist and
invariants report can flag operational-policy violations.

See:

* ``invariants.json`` → ``checks.all_bills_approved``
* ``ap_checklist.json`` → ``all_bills_approved``

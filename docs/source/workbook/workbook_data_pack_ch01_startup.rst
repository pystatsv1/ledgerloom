Workbook Data Pack (Canonical Inputs)
=====================================

This page contains the *exact* data used by the runnable workbook example:

``examples/workbook/ch01_startup``

Why this exists
---------------

Before you touch LedgerLoom, you should be able to:

1) see the raw “business events” (transactions)
2) enter them into a spreadsheet journal
3) produce an unadjusted trial balance
4) add adjustments, produce an adjusted trial balance
5) create closing entries, produce a post-close trial balance

LedgerLoom will later verify that your work is internally consistent — like a spelling/grammar checker
for the accounting cycle — but you should understand the “manual” flow first.

Canonical Chart of Accounts
---------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/config/chart_of_accounts.yaml
   :language: yaml
   :linenos:

Canonical Transactions (what you will journal)
----------------------------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/inputs/2026-01/transactions.csv
   :language: text
   :linenos:

Canonical Adjustments (starter file)
------------------------------------

This file starts empty on purpose — you will add adjusting entries in Workbook Chapter 3.

.. literalinclude:: ../../../examples/workbook/ch01_startup/inputs/2026-01/adjustments.csv
   :language: text
   :linenos:

Canonical Project Config (how LedgerLoom reads the project)
-----------------------------------------------------------

.. literalinclude:: ../../../examples/workbook/ch01_startup/ledgerloom.yaml
   :language: yaml
   :linenos:

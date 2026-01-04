Appendix — FAQ
==============

Why does LedgerLoom exist?
--------------------------

LedgerLoom is a MIT-licensed reference implementation that demonstrates how to
model accounting data as a canonical event log (entries + postings) and produce
reproducible financial reports.

Is LedgerLoom a replacement for accounting software?
----------------------------------------------------

No. LedgerLoom is designed as a learning and prototyping tool. It is intentionally
small, readable, and deterministic.

What is the difference between the “chapter runners” and the core library?
--------------------------------------------------------------------------

* The **core library** (``ledgerloom.core`` / ``ledgerloom.reports``) is reusable code.
* The **chapter runners** (``ledgerloom.chapters.*``) are demos that generate artifacts
  used in the documentation.

Where are the outputs written?
------------------------------

By default, chapter runners write to ``outputs/ledgerloom/``. Each chapter writes to
its own subfolder (e.g., ``outputs/ledgerloom/ch02``).
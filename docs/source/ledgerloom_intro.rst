LedgerLoom intro
================

LedgerLoom is a small open-source project intended to help learners understand:

- where accounting came from (paper journals and ledgers),
- why double-entry uses *debits/credits*,
- how those ideas map naturally to modern software (event logs + read models),
- how financial statements can be derived reproducibly from the underlying events.

What you can do today
---------------------

- Generate a tiny demo ledger and statements:

  .. code-block:: bash

     make ll-ch01

- Build the docs locally:

  .. code-block:: bash

     make docs
     ledgerloom-docs

Project philosophy
------------------

LedgerLoom aims to be:

- **Educational:** explain the “why,” not just the “how.”
- **Deterministic:** scripts produce the same outputs given the same inputs.
- **Tested:** automated checks so results are trustworthy.

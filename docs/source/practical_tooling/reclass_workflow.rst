Reclass workflow
================

LedgerLoom treats **unmapped transactions** as part of normal bookkeeping work.

When a transaction does not match any mapping rule, it is posted to a **suspense**
account (configured per source via ``suspense_account``). LedgerLoom then emits
helper files so you can fix mappings or manually reclassify.

Where to look
-------------

After you run:

.. code-block:: bash

   ledgerloom build

You will find these artifacts in:

``outputs/<run_id>/artifacts/``

* ``unmapped.csv`` — rows that were posted to suspense (with suggested regex patterns)
* ``reclass_template.csv`` — a copy/paste-friendly template for manual reclassification

The same ``unmapped.csv`` is also written by ``ledgerloom check`` under the check
outdir, but ``ledgerloom build`` copies it into the run folder so everything you
need travels with the run.

Config flags
------------

Two knobs control exception handling:

* ``strict_unmapped`` (project-level): if ``true``, the build aborts when any
  unmapped rows exist (run folder retained so you can fix mappings and re-run).
* ``suspense_account`` (per source): where unmapped transactions are posted.

Typical workflow
----------------

1. Run ``ledgerloom check`` to see unmapped rows early.
2. Add or refine mapping rules in ``ledgerloom.yaml``.
3. Re-run ``ledgerloom build``.
4. If you must close the period before perfect mappings, use
   ``reclass_template.csv`` to document reclass entries and apply them manually.


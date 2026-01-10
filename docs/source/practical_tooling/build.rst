ledgerloom build
================

``ledgerloom build`` creates an **immutable run folder** containing:

- a snapshot of inputs/config
- the check report produced during the build
- a trust manifest
- accounting artifacts (postings, trial balance, statements)

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** This produces the deliverables you share: postings + TB + statements.

   **Developer:** This is the “build artifact” you can checksum, archive, and reproduce.

   **Data pro:** This produces stable CSVs that are safe to load into notebooks/BI tools.

Run it
------

.. code-block:: bash

   ledgerloom build --project demo_books --run-id run-2026-01

Run folder layout
-----------------

.. code-block:: text

   demo_books/outputs/run-2026-01/
     source_snapshot/
     check/
     trust/
       manifest.json
       run_meta.json
     artifacts/
       postings.csv
       trial_balance.csv
       income_statement.csv
       balance_sheet.csv

Determinism proof (manifest hash)
---------------------------------

Because the trust manifest is content-addressed, you can verify determinism by hashing it:

.. code-block:: bash

   ledgerloom build --project demo_books --run-id run-a
   ledgerloom build --project demo_books --run-id run-b

   sha256sum demo_books/outputs/run-a/trust/manifest.json             demo_books/outputs/run-b/trust/manifest.json

If the inputs + config are unchanged, the hashes should match.

See also: :doc:`check` and :doc:`overview`.

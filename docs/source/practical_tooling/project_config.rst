Project configuration (ledgerloom.yaml)
=======================================

``ledgerloom.yaml`` controls how LedgerLoom interprets inputs and where it writes outputs.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** This is where you set the period, default accounts, and “what counts as an error.”

   **Developer:** This is the contract for build reproducibility: same config + same inputs ⇒ same outputs.

   **Data pro:** This is where you standardize dimensions (e.g., department) and output locations.

A minimal example
-----------------

.. code-block:: yaml

   schema_id: ledgerloom.project_config.v1

   project:
     name: demo_books
     period: 2026-01

   inputs:
     root: inputs

   outputs:
     root: outputs

   chart_of_accounts:
     path: config/chart_of_accounts.yaml

   mappings:
     root: config/mappings

   policy:
     # If true, unmapped rows fail the build/check (recommended once your rules are stable).
     strict_unmapped: false

     # Where to park truly-unknown rows if you choose to allow them.
     suspense_account: 9999

Key ideas
---------

Period
~~~~~~

The ``project.period`` value determines the default input folder:

- ``inputs/<period>/``

Strictness
~~~~~~~~~~

``policy.strict_unmapped`` controls whether unmapped rows are treated as errors.

- Start with ``false`` while you’re building rules.
- Switch to ``true`` once your mapping rules cover the expected input patterns.

Dimensions
~~~~~~~~~~

LedgerLoom can attach optional “dimensions” (columns like ``department``) to outputs.
If you do not configure dimensions, LedgerLoom still emits a consistent schema for core artifacts.

See also: :doc:`chart_of_accounts` and :doc:`check`.

Reclass workflow (turning unmapped rows into rules)
===================================================

The goal of the reclass workflow is to turn “unmapped” staging rows into **stable mapping rules**.
That’s the bridge between real-world messiness and a clean accounting pipeline.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** You’re encoding professional judgment (“this vendor is office supplies”) into a repeatable rule.

   **Developer:** You’re converting fuzzy input strings into a deterministic classification function.

   **Data pro:** You’re improving upstream labeling so downstream analyses are cleaner and more reliable.

Step 1 — run check
------------------

.. code-block:: bash

   ledgerloom check --project demo_books

Open:

- ``outputs/check/<period>/unmapped.csv``
- ``outputs/check/<period>/reclass_template.csv``

Step 2 — fill the template
--------------------------

Fill in ``reclass_template.csv`` rows you agree with. The key idea is:

- **match**: what should be recognized in the raw description
- **target account**: which COA code should receive the posting

Step 3 — generate rules
-----------------------

LedgerLoom writes/uses rule files in ``config/mappings/``. The intended workflow is:

- keep rule files small and readable
- commit them to version control
- rerun ``check`` until unmapped rows are acceptable

Step 4 — build
--------------

.. code-block:: bash

   ledgerloom build --project demo_books --run-id run-2026-01

Your run folder will include the same core accounting artifacts plus the trust manifest.

Practical tip
-------------

Start permissive (allow some unmapped rows) while bootstrapping, then tighten policy:

- set ``policy.strict_unmapped: true`` in ``ledgerloom.yaml`` once you trust your rules

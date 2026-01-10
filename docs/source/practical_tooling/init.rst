ledgerloom init
===============

``ledgerloom init`` creates a new LedgerLoom project folder with a minimal, safe default layout.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** This sets up a “books” folder that keeps source inputs, mappings, and outputs organized.

   **Developer:** This gives you a predictable project structure (good for version control and CI).

   **Data pro:** This ensures outputs land in a consistent place so downstream analysis is repeatable.

Create a project
----------------

.. code-block:: bash

   # Create a project folder named demo_books
   ledgerloom init demo_books

You’ll get a structure like:

.. code-block:: text

   demo_books/
     ledgerloom.yaml
     README.md
     config/
       chart_of_accounts.yaml
       mappings/
         .gitkeep
     inputs/
       2026-01/
         .gitkeep

Next steps
----------

1) Put CSV files in ``inputs/<period>/`` (by default the period is in ``ledgerloom.yaml``).

2) Edit:

- ``ledgerloom.yaml`` (project config)
- ``config/chart_of_accounts.yaml`` (chart of accounts)
- ``config/mappings/`` (optional rules)

3) Run:

.. code-block:: bash

   ledgerloom check --project demo_books
   ledgerloom build --project demo_books --run-id run-2026-01

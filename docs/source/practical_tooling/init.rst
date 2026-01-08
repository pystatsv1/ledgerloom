``ledgerloom init``
===================

``ledgerloom init`` creates a new LedgerLoom project folder you can run without writing Python.

It sets up:

* ``ledgerloom.yaml`` (project config template)
* ``config/chart_of_accounts.yaml`` (COA template)
* ``config/mappings/`` (placeholder folder for future mapping files)
* ``inputs/<period>/`` (where you drop CSVs)
* ``outputs/`` (where check/build runs write results)


Create a new project
--------------------

.. code-block:: bash

   ledgerloom init my_books --period 2026-01 --currency USD

Then:

.. code-block:: bash

   cd my_books
   ledgerloom check


Options
-------

``--name``
   Project display name (defaults to the directory name).

``--period``
   Accounting period in ``YYYY-MM`` (defaults to the current month).

``--currency``
   Currency code (defaults to ``USD``).


What to edit next
-----------------

1) Open ``ledgerloom.yaml`` and update:

   * the bank CSV column names under ``columns``
   * the required ``date_format`` (LedgerLoom does not guess)
   * your regex mapping ``rules``

2) Open ``config/chart_of_accounts.yaml`` and add the account codes you want to use.

3) Drop CSVs into ``inputs/<period>/`` and run:

.. code-block:: bash

   ledgerloom check

If there are errors, fix them using ``outputs/check/<period>/staging_issues.csv``.

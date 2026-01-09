Staging + ``ledgerloom check``
==============================

The ``ledgerloom check`` command is the *gatekeeper*.

It stages your input CSVs and reports problems *before* you attempt to build
postings, a trial balance, or financial statements. The intent is to prevent
"Crash on Entry" frustration by giving you fast, actionable feedback.

Quickstart
----------

From your project root (the folder that contains ``ledgerloom.yaml``):

.. code-block:: bash

   ledgerloom check

If your project lives elsewhere, point the command at it:

.. code-block:: bash

   ledgerloom check --project /path/to/my_books

By default, ``ledgerloom check`` reads inputs from:

``inputs/<period>/``

where ``<period>`` is ``project.period`` in your config.

Artifacts written
-----------------

``ledgerloom check`` writes four files to an output directory.

By default, the output directory is:

``<outputs.root>/check/<period>/``

For example:

.. code-block:: text

   outputs/check/2026-01/

You can override the output directory:

.. code-block:: bash

   ledgerloom check --outdir /tmp/ledgerloom_check

``checks.md``
    A human-readable report (what to fix first).

``staging.csv``
    A normalized staging table (one row per staged entry).

``staging_issues.csv``
    A machine-readable list of errors and warnings.

``unmapped.csv``
    Rows that did not match any mapping rule and were posted to the source suspense account.
    Use this as a worklist for authoring mappings.

Finding the bad row in Excel
----------------------------

The ``staging_issues.csv`` file includes ``source_row_number``.

This value is **1-based relative to the first data row** in the source CSV
(the header row is not counted). This lets you locate the problematic record
quickly in Excel or Google Sheets.

Exit codes
----------

``ledgerloom check`` exits with:

* ``0`` when there are **no errors** (warnings may be present)
* ``1`` when **errors** are present


Schema of ``staging_issues.csv``
--------------------------------

The exception list is designed to be filterable/sortable in a spreadsheet.

Columns:

``severity``
    ``error`` or ``warning``.

``code``
    A short machine-friendly code (e.g. ``parse_date``, ``unknown_account``).

``message``
    A human-friendly description of what went wrong.

``source_name`` / ``source_file``
    Where the issue came from (source name and filename).

``source_row_number``
    1-based row number (first data row = 1).

``column`` / ``raw_value``
    When available, the problematic column name and the raw value.

``account``
    When relevant, the account code involved.


Common issues
-------------

``config_load``
    ``ledgerloom.yaml`` could not be found or parsed. Make sure you run from the project root
    (or pass ``--project``).

``inputs_missing`` / ``no_files``
    The inputs directory doesn't exist, or the file pattern matched nothing.

``parse_date`` / ``parse_amount``
    The raw CSV value could not be parsed using the configured format/separators.

``unknown_account``
    A staged entry references an account code that is not present in the Chart of Accounts.

``unmapped_suspense``
    No mapping rule matched the description; the row landed in the suspense account (warning).

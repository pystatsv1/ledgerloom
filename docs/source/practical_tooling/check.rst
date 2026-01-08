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

By default, ``ledgerloom check`` reads inputs from:

``inputs/<period>/``

where ``<period>`` is ``project.period`` in your config.

Artifacts written
-----------------

``ledgerloom check`` writes three files to an output directory:

``checks.md``
    A human-readable report (what to fix first).

``staging.csv``
    A normalized staging table (one row per staged entry).

``staging_issues.csv``
    A machine-readable list of errors and warnings.

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

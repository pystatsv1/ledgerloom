ledgerloom check
================

``ledgerloom check`` is the *gatekeeper* command. It ingests your inputs into a staging table,
runs validations, and writes a small set of human- and machine-readable artifacts you can review
before you run ``ledgerloom build``.

Basic usage
-----------

Run check against a project folder::

  ledgerloom check --project my_books --outdir my_books/_out_check

Output artifacts
----------------

``ledgerloom check`` writes these files into the chosen outdir:

- ``checks.md`` — human-readable summary (errors/warnings + counts)
- ``staging.csv`` — normalized staged rows (what LedgerLoom *thinks* it read)
- ``staging_issues.csv`` — machine-readable issues table (errors and warnings)
- ``unmapped.csv`` — rows posted to suspense because no mapping rule matched
- ``reclass_template.csv`` — a helper template to reclass suspense rows later

Unmapped and suspense workflow
------------------------------

If a row does not match any mapping rule, LedgerLoom posts it to the source's ``suspense_account``.
This is reported as a warning (issue code ``unmapped_suspense``) by default.

If you want unmapped rows to *fail* your check (useful once your mappings are mature), set::

  strict_unmapped: true

in ``ledgerloom.yaml``. With strict mode on, unmapped suspense rows become errors and
``ledgerloom check`` returns a non-zero exit code.

unmapped.csv (copy/paste helpers)
---------------------------------

``unmapped.csv`` is designed to be “fix-forward”:

- ``suggested_pattern`` is a conservative ``(?i)`` regex derived from the original description.
- ``suggested_rule_yaml`` is a ready-to-paste YAML rule snippet with a placeholder account.

Example snippet (as written in the CSV)::

  - { pattern: '(?i)coffee', account: 'REPLACE_ME' }

You can paste that directly under a source's ``rules:`` list in ``ledgerloom.yaml`` and then replace
``REPLACE_ME`` with the correct account code from your chart of accounts.

ledgerloom suggest-mappings (dedupe to a YAML block)
----------------------------------------------------

If you have many unmapped rows, you probably don’t want to copy/paste one-by-one. The helper command
``ledgerloom suggest-mappings`` reads ``unmapped.csv``, dedupes similar rows, and prints a YAML block
you can review.

Print to stdout::

  ledgerloom suggest-mappings --unmapped my_books/_out_check/unmapped.csv

Write to a file::

  ledgerloom suggest-mappings --unmapped my_books/_out_check/unmapped.csv --out my_books/suggested_mappings.yaml

reclass_template.csv (reclassification helper)
----------------------------------------------

Alongside ``unmapped.csv``, ``ledgerloom check`` writes ``reclass_template.csv``. This file is a
*header-stable* starting point for creating reclassification entries (moving transactions out of the
suspense account once you know the right category).

Stable columns
^^^^^^^^^^^^^^

The column schema is defined centrally in code to prevent “column drift”:

- ``entry_id``
- ``date``
- ``description``
- ``original_amount``
- ``suspense_account``
- ``reclass_account``
- ``note``

How to use it
^^^^^^^^^^^^^

1) Fill in ``reclass_account`` for each row (e.g., ``Expenses:Meals``).

2) Optionally add a short ``note`` (why you classified it that way).

3) Use the completed template as your checklist for creating the actual reclass entry in your system.
   (Future LedgerLoom chapters will show how to encode and ingest these as entries.)

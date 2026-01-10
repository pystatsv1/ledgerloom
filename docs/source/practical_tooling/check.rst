ledgerloom check
================

``ledgerloom check`` is the gatekeeper: it loads your project, ingests your inputs, applies mappings,
and produces a *review package* (including reclass scaffolding) **without** creating a run folder.

.. admonition:: Translation box
   :class: translation-box

   **Accountant:** This is your “pre-close review” step: find unmapped rows and prepare reclasses.

   **Developer:** This is a fast validator you can run in CI before allowing a build.

   **Data pro:** This produces staging tables you can inspect to confirm schema + joins.

Run it
------

.. code-block:: bash

   ledgerloom check --project demo_books

By default, check outputs land in:

.. code-block:: text

   demo_books/outputs/check/<period>/

What it writes
--------------

The exact filenames may evolve, but the intent is stable:

- ``checks.md`` — human-readable report (deterministic; no timestamps)
- ``staging.csv`` — normalized ingested rows (after basic parsing)
- ``staging_issues.csv`` — parse/validation issues tied to staging rows
- ``unmapped.csv`` — rows that did not match a mapping rule
- ``reclass_template.csv`` — a template you can fill to create mapping rules

How to use it
-------------

1) Fix “hard” issues first (bad dates, malformed amounts).

2) Work through ``unmapped.csv``:

- add mapping rules in ``config/mappings/``
- or decide which ones should go to a suspense account

3) Use ``reclass_template.csv`` to encode “bookkeeper judgment” as stable rules.

See also: :doc:`reclass_workflow` and :doc:`build`.

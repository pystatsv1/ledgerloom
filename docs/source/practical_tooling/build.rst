ledgerloom build
================

``ledgerloom build`` runs the full trusted pipeline and writes an auditable run folder under
``outputs/<run_id>/`` (inputs/config snapshots, artifacts, and a trust manifest).

...

Exception-handling artifacts
----------------------------

In addition to core accounting outputs, build also includes::

  artifacts/reclass_template.csv

This template supports the suspense/reclassification workflow and is included in the trust manifest
so it is hashed and traceable like your other artifacts.

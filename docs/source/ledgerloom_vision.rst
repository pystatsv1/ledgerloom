LedgerLoom vision and roadmap
=============================

LedgerLoom is both a small Python library/CLI **and** a textbook-style set of chapters.

This page summarizes the roadmap from the Vision Document and links to each chapter page.

Chapter roadmap (18 chapters)
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 8 40 12

   * - #
     - Chapter
     - Status
   * - 1
     - :doc:`Journal vs Event Log & “Accounting data as code” <ledgerloom_ch01_journal_vs_eventlog>`
     - Implemented
   * - 2
     - :doc:`Debits/Credits as encoding <ledgerloom_ch02_debits_credits_encoding>`
     - Implemented
   * - 3
     - :doc:`Chart of Accounts as schema <ledgerloom_ch03_chart_of_accounts_schema>`
     - Implemented
   * - 4
     - :doc:`General Ledger as a database <ledgerloom_ch04_general_ledger_database>`
     - Implemented
   * - 5
     - :doc:`The accounting equation as invariant <ledgerloom_ch05_accounting_equation_invariant>`
     - Implemented
   * - 6
     - :doc:`Periods, accrual, and timing <ledgerloom_ch06_periods_accrual_timing>`
     - Implemented
   * - 7
     - :doc:`Adjusting entries as late-arriving data <ledgerloom_ch07_adjusting_entries_late_arriving_data>`
     - Implemented
   * - 8
     - :doc:`Closing as a controlled transformation <ledgerloom_ch08_closing_controlled_transformation>`
     - Implemented
   * - 9
     - :doc:`Accounts receivable lifecycle <ledgerloom_ch09_ar_lifecycle>`
     - Implemented
   * - 10
     - :doc:`Accounts payable lifecycle <ledgerloom_ch10_ap_lifecycle>`
     - Planned
   * - 11
     - :doc:`Inventory + COGS <ledgerloom_ch11_inventory_cogs>`
     - Planned
   * - 12
     - :doc:`Fixed assets + depreciation <ledgerloom_ch12_fixed_assets_depreciation>`
     - Planned
   * - 13
     - :doc:`Payroll as a multi-line event <ledgerloom_ch13_payroll_multiline_event>`
     - Planned
   * - 14
     - :doc:`Reconciliations as quality control <ledgerloom_ch14_reconciliations_quality_control>`
     - Planned
   * - 15
     - :doc:`Materiality & inconsequential misstatements <ledgerloom_ch15_materiality_misstatements>`
     - Planned
   * - 16
     - :doc:`Audit trail, provenance, explainability <ledgerloom_ch16_audit_trail_provenance_explainability>`
     - Planned
   * - 17
     - :doc:`Statement analysis with summary statistics <ledgerloom_ch17_statement_analysis_summary_statistics>`
     - Planned
   * - 18
     - :doc:`Forecasting + planning basics <ledgerloom_ch18_forecasting_planning_basics>`
     - Planned

Implementation cadence
----------------------

Each chapter ships with:

- a deterministic runner module under ``ledgerloom.chapters``
- sample input data (small, human-readable)
- generated artifacts under ``outputs/ledgerloom/chXX``
- golden-file tests to prevent regressions

Appendices
----------

Living reference docs:

- :doc:`Glossary <ledgerloom_appendix_glossary>`
- :doc:`FAQ <ledgerloom_appendix_faq>`
- :doc:`Implementation notes <ledgerloom_appendix_implementation_notes>`
- :doc:`Data model reference <ledgerloom_appendix_data_model_reference>`
- :doc:`Cookbook <ledgerloom_appendix_cookbook>`

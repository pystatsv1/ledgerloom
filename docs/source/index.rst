LedgerLoom
==========

LedgerLoom is a small open-source project (MIT license) that teaches accounting
*and* modern software engineering by building a deterministic, testable ledger
pipeline.

The documentation is organized into:

- **Start here**: what LedgerLoom is and where it is going
- **Engine**: the reusable core that powers the chapters
- **Chapters**: runnable scripts that generate reproducible artifacts
- **Appendices**: reference material (data model, glossary, cookbook)

.. toctree::
   :maxdepth: 1
   :caption: Start here

   ledgerloom_intro
   ledgerloom_vision
   changelog

.. toctree::
   :maxdepth: 1
   :caption: Engine (the reusable core)

   ledgerloom_engine_overview
   ledgerloom_engine_design_principles
   ledgerloom_engine_api_reference

.. toctree::
   :maxdepth: 1
   :caption: Chapters (runnable demos)

   ledgerloom_ch01_journal_vs_eventlog
   ledgerloom_ch02_debits_credits_encoding
   ledgerloom_ch03_posting_to_ledger
   ledgerloom_ch03_chart_of_accounts_schema
   ledgerloom_ch04_general_ledger_database
   ledgerloom_ch05_accounting_equation_invariant
   ledgerloom_ch06_periods_accrual_timing
   ledgerloom_ch07_adjusting_entries_late_arriving_data
   ledgerloom_ch08_closing_controlled_transformation
   ledgerloom_ch085_opening_next_period
   ledgerloom_ch09_ar_lifecycle
   ledgerloom_ch10_ap_lifecycle
   ledgerloom_ch11_inventory_cogs
   ledgerloom_ch12_fixed_assets_depreciation
   ledgerloom_ch13_payroll_register

.. toctree::
   :maxdepth: 1
   :caption: Future chapters (stubs)

   ledgerloom_ch13_payroll_multiline_event
   ledgerloom_ch14_reconciliations_quality_control
   ledgerloom_ch15_materiality_misstatements
   ledgerloom_ch16_audit_trail_provenance_explainability
   ledgerloom_ch17_statement_analysis_summary_statistics
   ledgerloom_ch18_forecasting_planning_basics

.. toctree::
   :maxdepth: 1
   :caption: Appendices

   ledgerloom_appendix_glossary
   ledgerloom_appendix_faq
   ledgerloom_appendix_cookbook
   ledgerloom_appendix_implementation_notes
   ledgerloom_appendix_data_model_reference
   practical_tooling/index

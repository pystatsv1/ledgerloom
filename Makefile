.DEFAULT_GOAL := help

PYTHON := python
SEED ?= 123
OUT_LL := outputs/ledgerloom


.PHONY: help ll-ch05 ll-ch06 ll-ch07 ll-ch08 ll-ch085 ll-ch09 ll-ch10
help:
	@echo "LedgerLoom (developer-friendly accounting) — targets:"
	@echo ""
	@echo "  ll-ch01    - Chapter 01 demo (journal vs event log) + artifacts"
	@echo "  ll-ch02    - Chapter 02 demo (debits/credits encoding) + artifacts"
	@echo "  ll-ch03    - Chapter 03 demo (posting to ledger) + artifacts"
	@echo "  ll-ch03-coa - Chapter 03 alt (COA as schema) + artifacts"
	@echo "  ll-ch03AccountsSchema - alias for ll-ch03-coa (kept for convenience)"
	@echo "  ll-ch04    - Chapter 04 demo (GL as database) + artifacts"
	@echo "  ll-ch05    - Chapter 05 demo (accounting equation invariant) + artifacts"
	@echo "  ll-ch06    - Chapter 06 demo (periods, accrual, timing) + artifacts"
	@echo "  ll-ch07    - Chapter 07 demo (adjusting entries as late-arriving data) + artifacts"
	@echo "  ll-ch08    - Chapter 08 demo (closing as controlled transformation) + artifacts"
	@echo "  ll-ch085  Run Chapter 08.5 demo (open next period + continuity)"
	@echo "  ll-ch09    - Chapter 09 demo (accounts receivable lifecycle) + artifacts"
	@echo "  ll-ch10    - Chapter 10 demo (accounts payable lifecycle) + artifacts"
	@echo "  ll-ci      - Tiny deterministic smoke (for CI)"
	@echo "  docs       - build HTML docs"
	@echo "  lint       - ruff check"
	@echo "  lint-fix   - ruff check with fixes"
	@echo "  test       - pytest"
	@echo "  clean      - remove generated outputs + build artifacts"


docs:
	python -m sphinx -b html docs/source docs/build/html


# --- CI smokes (small, deterministic) ---
.PHONY: ll-ci ll-ch05 ll-ch06
ll-ci:
	$(PYTHON) -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir $(OUT_LL) --seed $(SEED)


# --- Full demos ---
.PHONY: ll-ch01 ll-ch02 ll-ch03 ll-ch03-coa ll-ch03AccountsSchema ll-ch04 ll-ch05 ll-ch06
ll-ch01:
	$(PYTHON) -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir $(OUT_LL) --seed $(SEED)

ll-ch02:
	$(PYTHON) -m ledgerloom.chapters.ch02_debits_credits_encoding --outdir $(OUT_LL) --seed $(SEED)

ll-ch03:
	$(PYTHON) -m ledgerloom.chapters.ch03_posting_to_ledger --outdir $(OUT_LL) --seed $(SEED)

ll-ch03-coa:
	$(PYTHON) -m ledgerloom.chapters.ch03_chart_of_accounts_schema --outdir $(OUT_LL) --seed $(SEED)

ll-ch03AccountsSchema: ll-ch03-coa

ll-ch04:
	$(PYTHON) -m ledgerloom.chapters.ch04_general_ledger_database --outdir $(OUT_LL) --seed $(SEED)

ll-ch05:
	$(PYTHON) -m ledgerloom.chapters.ch05_accounting_equation_invariant --outdir $(OUT_LL) --seed $(SEED)


ll-ch06:
	$(PYTHON) -m ledgerloom.chapters.ch06_periods_accrual_timing --outdir $(OUT_LL) --seed $(SEED)

ll-ch07:
	$(PYTHON) -m ledgerloom.chapters.ch07_adjusting_entries_late_arriving_data --outdir $(OUT_LL) --seed $(SEED)

ll-ch08:
	$(PYTHON) -m ledgerloom.chapters.ch08_closing_controlled_transformation --outdir $(OUT_LL) --seed $(SEED)

ll-ch085: docs
	$(PYTHON) -m ledgerloom.chapters.ch085_opening_next_period --outdir $(OUT_LL) --seed $(SEED)

ll-ch09: docs
	$(PYTHON) -m ledgerloom.chapters.ch09_ar_lifecycle --outdir $(OUT_LL) --seed $(SEED)

ll-ch10: docs
	$(PYTHON) -m ledgerloom.chapters.ch10_ap_lifecycle --outdir $(OUT_LL) --seed $(SEED)


.PHONY: lint ll-ch05
lint:
	ruff check .


.PHONY: lint-fix ll-ch05
lint-fix:
	ruff check . --fix


.PHONY: test ll-ch05
test:
	pytest


.PHONY: clean ll-ch05
clean:
	@echo "Removing generated outputs in $(OUT_LL) + packaging artifacts"
	-@rm -rf $(OUT_LL)
	-@rm -rf dist build docs/build

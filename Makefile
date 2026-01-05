.DEFAULT_GOAL := help

PYTHON := python
SEED ?= 123
OUT_LL := outputs/ledgerloom


.PHONY: help
help:
	@echo "LedgerLoom (developer-friendly accounting) — targets:"
	@echo ""
	@echo "  ll-ch01    - Chapter 01 demo (journal vs event log) + artifacts"
	@echo "  ll-ch02    - Chapter 02 demo (debits/credits encoding) + artifacts"
	@echo "  ll-ch03    - Chapter 03 demo (posting to ledger) + artifacts"
	@echo "  ll-ch03-coa - Chapter 03 alt (COA as schema) + artifacts"
	@echo "  ll-ch04    - Chapter 04 demo (GL as database) + artifacts"
	@echo "  ll-ci      - Tiny deterministic smoke (for CI)"
	@echo "  docs       - build HTML docs"
	@echo "  lint       - ruff check"
	@echo "  lint-fix   - ruff check with fixes"
	@echo "  test       - pytest"
	@echo "  clean      - remove generated outputs + build artifacts"


docs:
	python -m sphinx -b html docs/source docs/build/html


# --- CI smokes (small, deterministic) ---
.PHONY: ll-ci
ll-ci:
	$(PYTHON) -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir $(OUT_LL) --seed $(SEED)


# --- Full demos ---
.PHONY: ll-ch01
ll-ch01:
	$(PYTHON) -m ledgerloom.chapters.ch01_journal_vs_eventlog --outdir $(OUT_LL) --seed $(SEED)

ll-ch02:
	$(PYTHON) -m ledgerloom.chapters.ch02_debits_credits_encoding --outdir $(OUT_LL) --seed $(SEED)

ll-ch03:
	$(PYTHON) -m ledgerloom.chapters.ch03_posting_to_ledger --outdir $(OUT_LL) --seed $(SEED)

ll-ch03-coa:
	$(PYTHON) -m ledgerloom.chapters.ch03_chart_of_accounts_schema --outdir $(OUT_LL) --seed $(SEED)

ll-ch04:
	$(PYTHON) -m ledgerloom.chapters.ch04_general_ledger_database --outdir $(OUT_LL) --seed $(SEED)


.PHONY: ll-ch04

.PHONY: lint
lint:
	ruff check .


.PHONY: lint-fix
lint-fix:
	ruff check . --fix


.PHONY: test
test:
	pytest


.PHONY: clean
clean:
	@echo "Removing generated outputs in $(OUT_LL) + packaging artifacts"
	-@rm -rf $(OUT_LL)
	-@rm -rf dist build docs/build

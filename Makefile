.DEFAULT_GOAL := help

PYTHON := python
SEED ?= 123
OUT_LL := outputs/ledgerloom


.PHONY: help
help:
	@echo "LedgerLoom (developer-friendly accounting) — targets:"
	@echo ""
	@echo "  ll-ch01    - Chapter 01 demo (journal vs event log) + artifacts"
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
	$(PYTHON) -m scripts.ledgerloom_ch01_journal_vs_eventlog --outdir $(OUT_LL) --seed $(SEED)


# --- Full demos ---
.PHONY: ll-ch01
ll-ch01:
	$(PYTHON) -m scripts.ledgerloom_ch01_journal_vs_eventlog --outdir $(OUT_LL) --seed $(SEED)


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

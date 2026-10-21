# Product Catalog Intelligence Platform — developer entry point.
#
# This file provides the dev loop only. Pipeline targets (data, ingest, quality, enrich,
# gold, db, load, embed, eval, app) are added by the feature that implements them — see
# docs/plan/ROADMAP.md. Do not add silent no-op stubs here.

SHELL := /bin/bash

VENV    := .venv
VENV_PY := $(VENV)/bin/python

# Prefer the project venv; fall back to the system interpreter on a fresh clone so that
# `make setup` works before the venv exists. Every other target requires the venv.
ifeq ($(wildcard $(VENV_PY)),)
PY := python3
else
PY := $(VENV_PY)
endif

RUFF := $(PY) -m ruff
MYPY := $(PY) -m mypy

.PHONY: help require-venv setup fmt lint typecheck test check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

require-venv:
	@test -x "$(VENV_PY)" || { \
		echo "error: $(VENV) not found — run 'make setup' first"; exit 1; }

setup: ## Create .venv and install runtime + dev dependencies
	@if command -v uv >/dev/null 2>&1; then \
		uv venv $(VENV) && \
		uv pip install --python $(VENV_PY) -r requirements.txt -r requirements-dev.txt; \
	else \
		python3 -m venv $(VENV) && \
		$(VENV_PY) -m pip install --upgrade pip && \
		$(VENV_PY) -m pip install -r requirements.txt -r requirements-dev.txt; \
	fi
	@echo "setup complete — try 'make check'"

fmt: require-venv ## Auto-format and fix lint
	$(RUFF) format .
	$(RUFF) check --fix .

lint: require-venv ## Lint without modifying files
	$(RUFF) check .

typecheck: require-venv ## Static type check (mypy, strict)
	$(MYPY) src

test: require-venv ## Run the test suite
	$(PY) -m pytest

check: require-venv ## Full gate: lint + format check + types + tests
	$(RUFF) check .
	$(RUFF) format --check .
	$(MYPY) src
	$(PY) -m pytest -q

clean: ## Remove caches and build artifacts (never data/)
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name '__pycache__' -not -path './$(VENV)/*' -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -not -path './$(VENV)/*' -delete
	@echo "clean complete"

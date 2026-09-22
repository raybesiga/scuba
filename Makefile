PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: test lint format-check format check contract smoke prepare
test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

contract:
	PYTHONPATH=src $(PYTHON) -m scuba contract

smoke:
	PYTHONPATH=src $(PYTHON) -m scuba generate --output artifacts/smoke

prepare:
	PYTHONPATH=src $(PYTHON) -m scuba prepare --output artifacts/m1-15000-seed-3501

lint:
	$(PYTHON) -m ruff check src tests

format-check:
	$(PYTHON) -m ruff format --check src tests

format:
	$(PYTHON) -m ruff format src tests

check: lint format-check test

# Optional local Radix presentation checks; uses already-installed, locked tools.
.PHONY: ui-check
ui-check:
	npm --prefix report-ui run check

DEMO_OUTPUT ?= artifacts/m5-demo
EVIDENCE_ROOT ?= .
.PHONY: demo
demo:
	PYTHONPATH=src $(PYTHON) -m scuba.demo build --evidence-root "$(EVIDENCE_ROOT)" --output "$(DEMO_OUTPUT)"

.PHONY: setup test smoke docs-check clean

# Prefer an explicit Python 3.11+ binary when available on PATH.
PYTHON ?= $(shell command -v python3.11 2>/dev/null || echo python3)
VENV ?= .venv

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e ".[dev]"

test:
	$(VENV)/bin/python -m pytest

smoke:
	$(VENV)/bin/python -m sre_work_sample.cli smoke

docs-check:
	$(PYTHON) scripts/validate_candidate_docs.py

clean:
	rm -rf $(VENV) .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

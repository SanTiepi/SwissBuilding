.PHONY: check lint format health health-fast test

## check: lint + format + health (full pre-merge gate)
check: lint format health
	@echo "All checks passed."

## lint: ruff lint (must be 0 errors)
lint:
	ruff check app/ tests/

## format: ruff format check (must be 0 diffs)
format:
	ruff format --check app/ tests/

## health: run all fitness functions
health:
	python scripts/pre_commit_check.py

## health-fast: route shell + compatibility only
health-fast:
	python scripts/pre_commit_check.py --fast

## test: run full backend test suite
test:
	python -m pytest tests/ -q

## fix: auto-fix lint + format
fix:
	ruff check --fix app/ tests/
	ruff format app/ tests/

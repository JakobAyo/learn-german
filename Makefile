# `make check` runs exactly what CI runs (0019). Keep the two in step.

.PHONY: check lint types test docs fmt

check: lint types test docs

lint:
	uv lock --check
	uv run --locked ruff check
	uv run --locked ruff format --check

types:
	uv run --locked mypy
	uv run --locked lint-imports

test:
	uv run --locked pytest -m "not nlp" --cov --cov-report=term-missing

docs:
	uv run --locked python tools/docs/validate_docs.py --docs-root docs

fmt:
	uv run ruff check --fix
	uv run ruff format

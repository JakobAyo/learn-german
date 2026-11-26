# `make check` runs what CI runs (0019), except the nlp job: run `make test-nlp` for it.
# Keep the two in step.

.PHONY: check lint types test test-nlp docs fmt

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

# Needs the spaCy model extra (0027), so `check` leaves it out; CI runs it as the nlp job.
test-nlp:
	uv run --locked --extra model pytest -m nlp

docs:
	uv run --locked python tools/docs/validate_docs.py --docs-root docs

fmt:
	uv run ruff check --fix
	uv run ruff format

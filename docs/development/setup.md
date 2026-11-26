---
title: Local setup
summary: Clone, install with uv, enable pre-commit and run make check; what each make target runs and how to install a released version.
status: active
updated: 2026-11-26
---

# Local setup

## Purpose

Gets a working development checkout in a few commands and explains the commands used day to day. Read this when setting up a new machine or when `make check` fails and you need to know what it runs.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) 0.9 or newer. uv installs the Python version pinned in `.python-version` (3.12) on first use.
- `make` and `git`.

## First-time setup

```bash
git clone git@github.com:<owner>/learn-german.git
cd learn-german
uv sync                           # creates .venv with the package and the dev group
uv run pre-commit install         # ruff and the lock check on every commit
make check                        # the same gates CI runs
uv run learn-german --version
```

Secrets go in a git-ignored `.env`; copy `.env.example` and fill in the keys. Tests never need them (R28).

The spaCy model (about 500 MB) is the optional extra `model` ([0027](../decisions/0027-settle-shared-dependencies-before-parallel-tracks.md)). `make check` does not need it. `make test-nlp` installs it on first use (`uv run --extra model`); to use the real extractor otherwise, install it once with `uv sync --extra model`. A later plain `uv sync` removes it again, `uv run` does not.

## Make targets

| Target | Runs | CI job |
|---|---|---|
| `make lint` | `uv lock --check`, `ruff check`, `ruff format --check` | `lint` |
| `make types` | `mypy` (strict, `src` and `tests`), `lint-imports` | `types` |
| `make test` | `pytest -m "not nlp"` with branch coverage, `fail_under = 85` | `test` |
| `make test-nlp` | `pytest -m nlp` with the `model` extra: the 0011 key table and the golden corpus against the real spaCy model ([NVV extraction](../system-design/nvv-extraction.md)) | `nlp` |
| `make docs` | `tools/docs/validate_docs.py --docs-root docs` | `docs` |
| `make check` | `lint`, `types`, `test` and `docs`; not `test-nlp`, so no model download | all but `nlp` |
| `make fmt` | `ruff check --fix`, `ruff format` | none |

pre-commit runs only the fast checks (ruff and the lock check). mypy, import-linter and the tests stay in `make check`, so commits stay quick.

## Common tasks

- **Add a dependency:** `uv add <pkg>` (or `uv add --group dev <pkg>`). Commit `pyproject.toml` and `uv.lock` together, or the lock check fails.
- **Refresh the vendored docs validator:** copy `validate_docs.py`, `build_index.py` and `docs_common.py` from the docs-architect skill into `tools/docs/`. They are excluded from ruff and mypy so they stay identical to the source.
- **Regenerate the docs index:** `python3 tools/docs/build_index.py --docs-root docs`.

## Installing a release

```bash
uv tool install git+https://github.com/<owner>/learn-german@v0.1.0
```

From M2 on, add the `model` extra; see [CI and releases](ci-and-releases.md#installing-a-release).

## Related

- [CI and releases](ci-and-releases.md)
- [Coding conventions](coding-conventions.md)
- [Testing strategy](testing-strategy.md)

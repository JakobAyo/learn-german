---
title: Gate main with required CI checks and branch protection
summary: main accepts only squash-merged PRs that pass lint, lock, mypy, import-linter, pytest with coverage, NLP tests, docs validation and a PR-title check.
status: active
updated: 2026-11-24
---

# Gate main with required CI checks and branch protection

## Context

R27 asks for ruff, a strict type check, pytest and the docs validator on every push. The owner also wants bugs caught before they reach `main`, with only the checks that matter. Some failures in this project are expensive and silent: a drifted chunk key breaks deduplication for good, and a note type change strands existing notes. The docs validator is currently only in `~/.claude/skills/`, so CI cannot run it.

## Decision

- Required jobs on every PR and push to `main`: `lint` (ruff check, ruff format check, `uv lock --check`), `types` (`mypy --strict`, import-linter), `test` (pytest without NLP tests, branch coverage of at least 85 %), `nlp` (real spaCy model, cached), `docs` (vendored validator), and a Conventional Commits check on the PR title.
- Branch protection on `main`: PR required, every job required, squash merge only, no force pushes. Secret scanning with push protection and Dependabot (actions and uv, weekly) are on.
- The docs validator scripts are vendored into `tools/docs/`.
- `make check` runs the same commands locally; pre-commit runs only the fast ruff and lock checks.
- Details and the list of what was left out are in [CI and releases](../development/ci-and-releases.md).

## Alternatives considered

- Only the four R27 checks: rejected. They do not catch layering erosion, a stale lock, or extractor regressions that only show with the real model.
- Python version matrix, CodeQL, gitleaks, PyPI publishing: left out as noise for a single-user local CLI. Each can be added if a need appears.
- Running NLP tests with the small model to save time: rejected. Its parses differ from `de_core_news_lg`, so the tests would check the wrong thing.

## Consequences

- Extends R27; update R27 to link here once this record is accepted.
- The `nlp` job is the slowest; caching the model wheel keeps it within a few minutes.
- The vendored validator can drift from the skill's copy. Refresh it by hand when the skill changes.

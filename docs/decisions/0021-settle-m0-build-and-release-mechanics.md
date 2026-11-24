---
title: Settle M0 build and release mechanics
summary: uv_build backend, uv.lock refreshed by the release workflow, pre-commit on the locked ruff, and layer stubs so import-linter enforces 0018 now.
status: active
updated: 2026-11-24
---

# Settle M0 build and release mechanics

## Context

M0 ([Roadmap](../product/roadmap.md)) turns 0018 to 0020 into a working repository. Several small choices were left open: the build backend, how the release PR keeps `uv.lock` in step (the first pitfall in [CI and releases](../development/ci-and-releases.md)), where pre-commit gets ruff from, and how import-linter can check layers that hold no code yet.

## Decision

- **Build backend:** `uv_build`. The project already uses uv for everything else, and the backend handles the `src/` layout and package data with no configuration.
- **`uv.lock` on release PRs:** a step in `release-please.yml` checks out the release branch, runs `uv lock` and pushes if the lock changed, using `RELEASE_PLEASE_TOKEN` so the required checks run again.
- **pre-commit:** local hooks that call `uv run --locked ruff …` and `uv lock --check`, so the hooks use the same ruff version as CI and there is no second version to keep in step.
- **Layer stubs:** `domain/`, `application/`, `adapters/`, `ports.py` and `bootstrap.py` exist as documented empty modules, so the layers and forbidden-import contracts are active before any feature code lands.
- **Vendored docs validator:** excluded from ruff and mypy, so it stays a byte-for-byte copy of the skill's scripts.
- **Starting version:** `0.0.0` in `pyproject.toml` and the manifest; the first `feat:` makes 0.1.0.

## Alternatives considered

- `hatchling`: works equally well; rejected only to avoid a second tool where uv already fits.
- release-please `extra-files` TOML updater for `uv.lock`: no extra workflow step, but the jsonpath filter over `[[package]]` depends on release-please's TOML parser, and an error would only show on the release PR. `uv lock` cannot be wrong.
- Upstream `ruff-pre-commit` hooks: pin their own ruff version, which drifts from the lock and can format differently from CI.
- Optional layers in import-linter: the contract would pass silently if a layer were renamed or never created.

## Consequences

- The release workflow pushes one extra commit to each release PR when the lock changes.
- `uv run` in hooks means a fresh clone must run `uv sync` before the first commit; [Local setup](../development/setup.md) says so.
- Refreshing the vendored validator is a manual copy, as 0019 already notes.

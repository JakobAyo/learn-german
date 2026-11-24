---
title: Build a single-user Python CLI in a public repository
summary: The tool is a Python 3.12+ CLI managed with uv, used by one person, published as a public repo with nothing personal in it.
status: active
updated: 2026-11-24
---

# Build a single-user Python CLI in a public repository

## Context

Only the owner will use the tool, and runs are started by hand when new material is available. The owner wants the code in a public GitHub repository so that CI minutes are unlimited. The core NLP library for German, spaCy, is Python.

## Decision

- The tool is a command-line program that runs on the owner's machine. There are no accounts, server or web UI.
- Python 3.12+, with `uv` for dependencies and the lock file.
- The repository is public. It must hold no secrets, personal paths, personal config, mined sentences or copyrighted source text. Secrets come from environment variables or a git-ignored `.env`; config and state live in XDG per-user directories.
- CI on GitHub Actions runs `ruff`, a strict type check, `pytest` and the docs validator. It needs no secrets: external services are mocked.

## Alternatives considered

- Local web UI: rejected for now. It adds a frontend without serving a goal, since there is no review step (see [0005](0005-push-cards-automatically-with-tagging-and-dry-run.md)).
- Hosted multi-device service: rejected. It needs auth, hosting and storage for a single user.
- Browser extension: rejected. Existing extensions already cover single-word mining, and chunk extraction needs a full NLP pipeline.
- Private repository: rejected. CI minutes are limited.

## Consequences

- Keep the core as a library under a thin CLI, so another front end can be added later without a rewrite.
- Every test fixture must be synthetic or freely licensed text.
- Committing a real article, an API key or an Anki profile path is a defect, even in tests or examples.

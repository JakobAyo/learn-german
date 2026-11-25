---
title: Development
summary: Local setup, dependencies and NLP models, and how to run the extractor.
---

# Development

Local setup, dependencies and NLP models, and how to run the extractor.

## What belongs here

- Environment and dependency setup (Python, spaCy models)
- Command usage and common tasks
- Debugging tips

## What does not belong here

- Architecture (system-design/)
- Anki add-on configuration details (integrations/)

<!-- docs-index:start -->

## Contents

- [CI and releases](ci-and-releases.md) `[draft]` — CI jobs that gate main, repository settings, the Conventional Commits PR-title rule, and how release-please produces versions, tags and CHANGELOG.md.
- [Coding conventions](coding-conventions.md) `[draft]` — Typing, naming, error handling, I/O boundaries, configuration and pull-request rules that every change follows.
- [Configuration](configuration.md) — Every setting with its default, environment variable and TOML key, where config.toml and .env are read from, and the order in which sources override each other.
- [Local setup](setup.md) — Clone, install with uv, enable pre-commit and run make check; what each make target runs and how to install a released version.
- [Testing strategy](testing-strategy.md) `[draft]` — Test layers from pure unit to manual release checks, fakes and contract tests, the no-network and synthetic-fixture rules, and coverage targets.

<!-- docs-index:end -->

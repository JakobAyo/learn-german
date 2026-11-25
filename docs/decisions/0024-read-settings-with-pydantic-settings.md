---
title: Read settings with pydantic-settings, layered flag, environment, .env and TOML
summary: pydantic-settings layers flags, LEARN_GERMAN_ variables, .env and config.toml; unknown TOML keys fail and the hint language is an ISO 639 code.
status: active
updated: 2026-11-25
---

# Read settings with pydantic-settings, layered flag, environment, .env and TOML

## Context

M1 needs one place that reads settings with the precedence flag > environment > config file > default (R12, R25), secrets from the environment or a git-ignored `.env`, and a hint language that is only required when generation runs (R16). The [Roadmap](../product/roadmap.md) left the library open and recommended `pydantic-settings`.

## Decision

- **Library:** `pydantic-settings`, plus `platformdirs` for the XDG paths. pydantic stays out of `domain/`, `ports` and `application/`; import-linter forbids it there.
- **Sources, highest first:** command-line flags, environment variables, `.env` in the working directory, `~/.config/learn-german/config.toml`, defaults. A flag that was not given (`None`) does not override anything.
- **Names:** environment variables use the prefix `LEARN_GERMAN_` (`LEARN_GERMAN_CAP`). The API key keeps its standard name, `ANTHROPIC_API_KEY`. TOML keys are the field names (`hint_language`).
- **Strictness:** an unknown key in `config.toml` is an error, because it is almost always a typo. Unknown variables in `.env` are ignored, because that file is often shared with other tools.
- **Hint language:** an ISO 639 code such as `en`, so the `HintLanguage` note field and prompt get a stable value. `Settings.require_hint_language()` raises `ConfigError` only when generation needs it.
- **Errors:** invalid values, unknown keys and broken TOML raise `ConfigError` (fatal) with the file and variable to fix.

The settings and their environment names are listed in [Configuration](../development/configuration.md).

## Alternatives considered

- Hand-written loader on `tomllib` and `os.environ`: no extra dependency, but type coercion, validation messages and `.env` parsing would all be ours to write and test.
- `dynaconf`: more features (profiles, many formats) than one user with one config file needs, and weaker typing.
- `.env` in the config directory instead of the working directory: safer for an installed tool, but R25 describes a git-ignored `.env`, which means the checkout. Can be added as a second location later.

## Consequences

- The Anthropic SDK in M5 already depends on pydantic, so the extra weight is small, and M5 can reuse pydantic to validate LLM output.
- Each call to `load_settings` builds a small subclass to point at the right `config.toml`, so tests can pass their own file and the XDG path is resolved at call time, not import time.
- Tests remove every `LEARN_GERMAN_*` and `ANTHROPIC_*` variable and run in a temporary working directory, so a developer's own `.env` never leaks into a test.

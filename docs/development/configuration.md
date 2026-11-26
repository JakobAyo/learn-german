---
title: Configuration
summary: Every setting with its default, environment variable and TOML key, where config.toml and .env are read from, and the order in which sources override each other.
status: active
updated: 2026-11-26
---

# Configuration

## Purpose

Lists what can be configured and where. Read this before adding a setting or when a value does not take effect. The choices behind it are in [0024](../decisions/0024-read-settings-with-pydantic-settings.md); the code is `src/learn_german/config.py`, the only module that reads the environment.

## Precedence

Highest first:

1. Command-line flag, for example `sync --cap 3`
2. Environment variable
3. `.env` in the directory `learn-german` is run from (git-ignored)
4. `~/.config/learn-german/config.toml` (the XDG config directory)
5. Default

## Settings

| TOML key | Environment variable | Default | Meaning |
|---|---|---|---|
| `hint_language` | `LEARN_GERMAN_HINT_LANGUAGE` | none, required for generation | ISO 639 code of the translation-prompt language, for example `en` (R16) |
| `cap` | `LEARN_GERMAN_CAP` | `10` | Most new chunks per `sync`, each giving two notes (R12) |
| `provider` | `LEARN_GERMAN_PROVIDER` | `anthropic` | LLM provider (R17) |
| `model` | `LEARN_GERMAN_MODEL` | `claude-opus-5-5` | LLM model ID (0015) |
| `deck` | `LEARN_GERMAN_DECK` | `learn-german::chunks` | Anki deck the tool owns (0016) |
| `anki_connect_url` | `LEARN_GERMAN_ANKI_CONNECT_URL` | `http://127.0.0.1:8765` | AnkiConnect endpoint of the running Anki app (0003) |
| `database_path` | `LEARN_GERMAN_DATABASE_PATH` | `~/.local/share/learn-german/learn-german.db` | SQLite state ([Data model](../data/data-model.md)); `~` is expanded |
| `anthropic_api_key` | `ANTHROPIC_API_KEY` | none | Claude API key; keep it in the environment or `.env`, not in `config.toml` |

Example `config.toml`:

```toml
hint_language = "en"
cap = 5
```

## Rules

- An unknown key in `config.toml` is an error, so a typo does not go unnoticed. Unrelated variables in `.env` are ignored.
- An invalid value in any source stops the command with a message that names the setting.
- The hint language and the API key are checked only by the commands that need them, so `add` and `status` work without them.

## Related

- [Local setup](setup.md)
- [Coding conventions](coding-conventions.md)

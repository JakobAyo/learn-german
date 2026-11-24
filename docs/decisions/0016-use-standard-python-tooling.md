---
title: Use standard Python tooling for CLI, types, fetching and NLP
summary: typer for the CLI, mypy --strict, httpx and trafilatura for fetching, spaCy de_core_news_lg, a light-verb data file, timestamp run IDs and a learn-german deck.
status: active
updated: 2026-11-24
---

# Use standard Python tooling for CLI, types, fetching and NLP

## Context

Several technical choices have no effect on learning and only need to be made once, so the implementation is consistent. The owner asked for well-established defaults that can be overruled later.

## Decision

| Concern | Choice |
|---|---|
| CLI framework | `typer` |
| Strict type check in CI | `mypy --strict` |
| HTTP client | `httpx` |
| Article main-text extraction | `trafilatura` |
| spaCy model | `de_core_news_lg` (CPU, fast); the transformer model may be added later as an option |
| Light-verb whitelist | A starter list (*bringen, nehmen, stellen, treffen, führen, kommen, geben, halten, …*) in a data file in the repo, not in code |
| Run ID | UTC timestamp, for example `run-20261124-1530` |
| Default deck name | `learn-german::chunks` (configurable, see [0003](0003-push-notes-live-through-ankiconnect.md)) |

## Alternatives considered

- `click` or `argparse`: `typer` builds on `click` and takes its options from type hints, which suits a strictly typed code base.
- `pyright`: works as well; `mypy` was picked as the more common default in Python CI.
- `requests`: `httpx` has the same style, plus timeouts and an async API if needed later.
- `newspaper3k` or a hand-written readability pass: `trafilatura` is maintained and scores well at extracting news article text.
- The transformer spaCy model as default: rejected for v1, because it is slower and much larger; switch if parse quality on NVVs is poor.

## Consequences

- Each choice is local to one module, so changing one later does not touch the others.
- The spaCy model is a download step in setup, documented in `development/`.

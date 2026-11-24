---
title: Code architecture
summary: Ports-and-adapters layout of the Python package, the dependency rule, every port with its v1 adapter and fake, and the patterns used where.
status: draft
updated: 2026-11-24
---

# Code architecture

## Purpose

Describes how the code is organised so that each seam in the Deferred table of [Requirements](../product/requirements.md) is a new adapter rather than a refactor. The choice is recorded in [0018](../decisions/0018-structure-code-as-ports-and-adapters.md). Read this before adding a module, a plug-in or a dependency between packages.

## Layers and the dependency rule

```
          cli  (typer commands, presenters)
           │
           ▼
      bootstrap  (composition root: reads config, wires adapters)
       │      │
       ▼      ▼
 application  adapters  (sqlite, spacy/nvv, news-url, file, anthropic, ankiconnect)
 (use cases)    │
       │        │ implements
       ▼        ▼
         ports  (Protocols)
           │
           ▼
         domain  (pure: value objects, entities, errors, rules)
```

- `domain` imports only the standard library.
- `application` imports `domain` and `ports`, never an adapter or an I/O library.
- `adapters` import `domain`, `ports` and their own third-party library. Adapters never import each other.
- Only `bootstrap` and `cli` import adapters.

The rule is enforced in CI by import-linter contracts in `pyproject.toml`, not by review.

## Package layout

```
src/learn_german/
  domain/
    models.py            # ChunkKey, RunId, Source, Candidate, NoteDraft, RunSummary
    errors.py            # LearnGermanError → FatalError | ItemError
  ports.py               # all Protocols
  application/
    add_sources.py
    sync.py
    status.py
    reextract.py
    selection.py         # FilterChain, cap, OccurrencePicker
  adapters/
    sources/             # local_file.py, news_url.py
    extractors/nvv/      # parse.py, match.py, keys.py, data/*.txt|tsv
    ranking/             # occurrence.py
    llm/                 # anthropic.py, caching.py, prompts/card_v1.md
    anki/                # client.py, gateway.py, note_types.py, templates/
    storage/sqlite/      # uow.py, repositories.py, migrations/NNNN_*.sql
  config.py
  bootstrap.py
  cli/
    app.py               # commands only, no logic
    presenters.py        # tables and summaries
tests/
  fakes/                 # one fake per port, shared by all test layers
  unit/  contract/  integration/  nlp/  e2e/
tools/
  docs/                  # vendored docs validator
```

## Ports

| Port | v1 adapter | Test double | Requirement |
|---|---|---|---|
| `SourceAdapter` | `LocalFileSource`, `NewsUrlSource` | `FakeSource` | R4, R5 |
| `ChunkExtractor` | `NvvExtractor` | `FakeExtractor` | R8, R9 |
| `CandidateFilter` | `AlreadyInDeckFilter` | not needed (pure) | R11, R14 |
| `Ranker` | `OccurrenceRanker` | not needed (pure) | R13 |
| `LLMProvider` | `AnthropicProvider`, wrapped by `CachingProvider` | `FakeProvider` | R17 |
| `AnkiGateway` | `AnkiConnectGateway` | `FakeAnkiGateway` (in-memory deck) | R19, R20 |
| `UnitOfWork` and repositories | SQLite | SQLite `:memory:` (real code) | R24 |
| `Clock` | `SystemClock` | `FixedClock` | run IDs |

Ports are `typing.Protocol`s, so adapters and fakes need no inheritance and mypy checks them structurally.

## Patterns and where they apply

| Pattern | Where | Why |
|---|---|---|
| Ports and adapters | Whole layout | Every deferred feature becomes a new adapter. Use cases are testable without I/O. |
| Strategy | Sources, extractors, rankers, LLM providers, occurrence picker | Swapped by config, chosen in the composition root. |
| Composite | `FilterChain` | Known-item filters (R14) are appended, and `sync` does not change. |
| Decorator | `CachingProvider` around any `LLMProvider` | Caching is written once; DeepSeek or `claude -p` get it for free. |
| Repository and unit of work | SQLite storage | One transaction per source in `add` and per chunk in `sync` gives the partial-failure rules of [0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md). |
| Builder | `NoteBuilder` | One `CardContent` becomes two `NoteDraft`s with fields and tags in a single tested place. |
| Registry | Name to plug-in maps in `bootstrap` | A plain dict. No entry points until third-party plug-ins exist. |
| Composition root | `bootstrap.py` | Constructor injection, no globals, no DI framework. Tests pass overrides. |
| Value object | `ChunkKey`, `RunId` | Validated once at creation, immutable, safe to use as dict keys. |

Not used on purpose: abstract base class hierarchies (Protocols suffice), a service locator, async (one user and sequential calls), a generic `utils` module.

## Error model

| Type | Meaning | Examples | `sync` reaction |
|---|---|---|---|
| `FatalError` | Every further step would fail | `AnkiUnavailable`, `MissingCredentials`, `ConfigError`, `NoteTypeMismatch` | Stop at once, print summary, exit 2 |
| `ItemError` | Only this source or chunk failed | `SourceFetchError`, `GenerationError`, `PushError` | Record the error, continue, exit 1 at the end |

Adapters catch their library's exceptions and re-raise one of these with `raise … from exc`. Only the use-case loop catches `ItemError`; nothing catches `FatalError` except the CLI, which turns it into a message and an exit code.

## Data flow

```
ref ─► SourceAdapter ─► Source(text) ─► ChunkExtractor ─► Candidate[]            (add)

Candidate[] ─► FilterChain ─► Ranker ─► cap ─► OccurrencePicker ─► CardRequest
            ─► LLMProvider ─► CardContent ─► NoteBuilder ─► NoteDraft×2 ─► AnkiGateway   (sync)
```

## Related

- [Pipeline](pipeline.md)
- [Coding conventions](../development/coding-conventions.md)
- [Testing strategy](../development/testing-strategy.md)

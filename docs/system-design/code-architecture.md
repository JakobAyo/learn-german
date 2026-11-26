---
title: Code architecture
summary: Ports-and-adapters layout of the Python package, the dependency rule, every port with its v1 adapter and fake, and the patterns used where.
status: draft
updated: 2026-11-26
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
           │
           ▼
         config  (settings: the only module that reads the environment)
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

- `domain` imports only the standard library, and not its I/O modules (`os`, `pathlib`, `sqlite3`).
- `application` imports `domain` and `ports`, never an adapter, `config` or an I/O library.
- `adapters` import `domain`, `ports` and their own third-party library. Adapters never import each other.
- `config` may import `domain` (for `ConfigError`); only `bootstrap` and `cli` import `config`.
- Only `bootstrap` and `cli` import adapters.

The rule is enforced in CI by three import-linter contracts in `pyproject.toml`, not by review: the layer order above, a forbidden-modules list for `domain`, `ports` and `application` (extended as milestones add I/O libraries), and independence of the packages under `adapters/`.

## Package layout

```
src/learn_german/
  domain/
    models.py            # ChunkKey, RunId, Source, Candidate, ChunkState, PendingChunk,
                         # CardRequest, CardContent, NoteDraft, RunSummary, enums
    errors.py            # LearnGermanError → FatalError | ItemError
  ports.py               # all Protocols, including the repositories and UnitOfWork
  application/
    selection/           # filters.py   FilterChain, AlreadyInDeckFilter
                         # ranking.py   OccurrenceRanker
                         # cap.py       cap
                         # picker.py    ShortestSentencePicker
                         # selector.py  ChunkSelector, SelectedChunk
    generation/          # caching.py   CachingProvider, cache_key
                         # checks.py    CheckedProvider, check_card
    notes/               # builder.py   NoteBuilder
                         # tags.py      run_tags, TOOL_TAG
    extraction.py        # extract_candidates, the 0017 rules (plan/refresh_candidates)
    add_sources.py       # AddSources, SourceOutcome, AddSummary
    status.py            # ShowStatus, StatusReport
    reextract.py         # Reextract
    sync.py              # M7
  adapters/
    nlp/                 # extractor.py (NvvExtractor), parse.py (the only spaCy module),
                         # tokens.py, match.py, keys.py, lexicon.py,
                         # data/light_verbs.txt, data/spelling_variants.tsv
    llm/                 # claude.py (AnthropicProvider), prompt.py (PROMPT_VERSION, renderer),
                         # schema.py (pydantic output schema), errors.py, prompts/card_v1.md
    anki/                # client.py (AnkiConnectClient), gateway.py (AnkiConnectGateway),
                         # note_types.py (NoteTypeSpec), errors.py, templates/*.html|css
    storage/sqlite/      # database.py, uow.py, repositories.py, migrations/NNNN_*.sql
    sources/             # local_file.py (LocalFileSource), news_url.py (NewsUrlSource),
                         # text.py (normalise_text, content_hash)
    clock.py             # SystemClock
  config.py
  bootstrap.py           # composition root: extractor registry, source adapters,
                         # Overrides, ingest_services()
  cli/
    app.py               # create_app(overrides): commands only, no logic
    presenters.py        # plain-text lines and summaries
tests/
  fakes/                 # shared fakes: FakeAnkiGateway, FakeProvider, FixedClock,
                         # FakeSource, FakeExtractor
  unit/  contract/  integration/  nlp/  e2e/
tools/
  docs/                  # vendored docs validator
  eval/                  # manual prompt evaluation, never run in CI
```

## Ports

| Port | v1 adapter | Test double | Requirement |
|---|---|---|---|
| `SourceAdapter` | `NewsUrlSource`, `LocalFileSource`, asked in that order | `FakeSource` | R4, R5 |
| `ChunkExtractor` | `NvvExtractor` | `FakeExtractor` (trigger words, no spaCy) | R8, R9 |
| `CandidateFilter` | `AlreadyInDeckFilter`, combined by `FilterChain` (in `application/selection/filters.py`) | not needed (no I/O) | R11, R14 |
| `Ranker` | `OccurrenceRanker` (in `application/selection/ranking.py`) | not needed (pure) | R13 |
| `OccurrencePicker` | `ShortestSentencePicker` (in `application/selection/picker.py`) | not needed (pure) | [0032](../decisions/0032-feed-cards-from-the-shortest-sentence-of-ten-words.md) |
| `LLMProvider` | `AnthropicProvider`, wrapped by `CheckedProvider` and then `CachingProvider` | `FakeProvider` | R17 |
| `AnkiGateway` | `AnkiConnectGateway` | `FakeAnkiGateway` (in-memory deck) | R19, R20 |
| `UnitOfWork` with `SourceRepository`, `CandidateRepository`, `ChunkStateRepository`, `LLMCacheRepository` | `SqliteUnitOfWork` | SQLite `:memory:` (real code) | R24 |
| `Clock` | `SystemClock` | `FixedClock` | run IDs |

Ports are `typing.Protocol`s, so adapters and fakes need no inheritance and mypy checks them structurally. The plug-in port signatures were set in M1 so M2, M4, M5 and M6 could be built in parallel; each milestone refined only its own port:

- `LLMProvider` has a `prompt_version` property next to `name` and `model`, so the cache key changes with the prompt ([0035](../decisions/0035-version-the-card-prompt-as-a-template-with-a-pinned-hash.md)). Decorators pass all three through.
- `CandidateRepository.pending_chunks()` returns every chunk key that is not done locally, with its occurrence count and missing note kinds, ordered by key. It is the input of selection ([Data model](../data/data-model.md#pending-chunks)).
- `OccurrencePicker` was added in M4.
- `SourceRepository.find_id` takes the reference or the hash alone, `SourceRepository.replace` overwrites a stored source in place, and `CandidateRepository.remove` deletes a source's occurrences, for `add --force` and `reextract` ([0042](../decisions/0042-recognise-known-sources-before-fetching-and-refresh-them-in-place.md)).
- `AnkiGateway.existing_keys` reads notes of the tool's note type anywhere in the collection, not only in the deck ([0039](../decisions/0039-read-existing-keys-per-note-type-across-the-collection.md)).

Some v1 strategies live in `application/`, not `adapters/`, because they do no I/O: the ranker and the picker are pure, and `AlreadyInDeckFilter` reaches Anki only through the `AnkiGateway` port, so its tests use `FakeAnkiGateway`. `ChunkSelector` in `application/selection/selector.py` runs pending chunks through filter, ranker, cap and picker.

The ingest use cases (`AddSources`, `ShowStatus`, `Reextract`) are described in [Ingest](ingest.md). `AddSources.run` and `Reextract.run` yield one outcome per source after its unit of work commits, so the CLI prints progress as it happens ([0045](../decisions/0045-build-the-cli-with-create-app-and-stream-outcomes.md)).

`with uow:` is one transaction: it commits when the block ends normally and rolls back when it raises. Tables and the chunk status are in [Data model](../data/data-model.md).

## Patterns and where they apply

| Pattern | Where | Why |
|---|---|---|
| Ports and adapters | Whole layout | Every deferred feature becomes a new adapter. Use cases are testable without I/O. |
| Strategy | Sources, extractors, rankers, LLM providers, occurrence picker (`ShortestSentencePicker` in v1) | Swapped by config, chosen in the composition root. |
| Composite | `FilterChain` | Known-item filters (R14) are appended, and `sync` does not change. |
| Decorator | `CheckedProvider` and `CachingProvider` around any `LLMProvider`, wired as `CachingProvider(CheckedProvider(provider), uow, clock)` | Sanity checks and caching are written once; DeepSeek or `claude -p` get them for free. Checks sit inside the cache, so content that fails them is never cached ([0036](../decisions/0036-check-card-content-then-cache-it-in-its-own-transaction.md)). |
| Repository and unit of work | SQLite storage | One transaction per source in `add` and per chunk in `sync` gives the partial-failure rules of [0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md). |
| Builder | `NoteBuilder` | One `CardContent` becomes two `NoteDraft`s with fields and tags in a single tested place. |
| Registry | Name to plug-in maps in `bootstrap`, starting with `extractor_registry()` | A plain dict. No entry points until third-party plug-ins exist. |
| Composition root | `bootstrap.py` | Constructor injection, no globals, no DI framework. Tests pass `Overrides` to `create_app` ([0045](../decisions/0045-build-the-cli-with-create-app-and-stream-outcomes.md)). |
| Value object | `ChunkKey`, `RunId` | Validated once at creation, immutable, safe to use as dict keys. |

Not used on purpose: abstract base class hierarchies (Protocols suffice), a service locator, async (one user and sequential calls), a generic `utils` module.

## Error model

| Type | Meaning | Examples | `sync` reaction |
|---|---|---|---|
| `FatalError` | Every further step would fail | `ConfigError`, `MissingCredentialsError`, `DatabaseError`, `NlpModelMissingError`, `AnkiUnavailableError`, `NoteTypeMismatchError`, `LLMAccessError`, `AnkiActionError` | Stop at once, print summary, exit 2 |
| `ItemError` | Only this source or chunk failed | `SourceFetchError`, `DuplicateSourceError`, `GenerationError`, `PushError`, `LLMRequestError` | Record the error, continue, exit 1 at the end |

Shared errors live in `domain/errors.py`. An adapter that needs its own error subclasses a domain error in its own `errors.py` ([0026](../decisions/0026-run-m2-m4-m5-m6-as-parallel-tracks.md)): `LLMAccessError` (the provider refused the key, account or model) and `LLMRequestError` (one call failed after retries) in `adapters/llm/` ([0037](../decisions/0037-call-claude-with-a-json-schema-and-split-errors-into-fatal-and-item.md)), and `AnkiActionError` (an AnkiConnect action failed or answered in the wrong shape) in `adapters/anki/`, which the gateway narrows to a `PushError` when only one note is affected ([0040](../decisions/0040-add-notes-one-call-each-and-split-ankiconnect-errors.md)).

Adapters catch their library's exceptions and re-raise one of these with `raise … from exc`. Only the use-case loop catches `ItemError`; nothing catches `FatalError` except the CLI, which turns it into a message and an exit code. `SourceFetchError` covers every source that cannot be read: no adapter for the reference, a missing or non-UTF-8 file, a page robots.txt forbids, a refused or paywalled page, a timeout, or too little text.

## Data flow

```
ref ─► SourceAdapter ─► Source(text) ─► ChunkExtractor ─► Candidate[]            (add)

pending_chunks() ─► FilterChain ─► Ranker ─► cap ─► OccurrencePicker ─► CardRequest
                 ─► LLMProvider ─► CardContent ─► NoteBuilder ─► NoteDraft×2 ─► AnkiGateway   (sync)
```

## Related

- [Pipeline](pipeline.md)
- [Coding conventions](../development/coding-conventions.md)
- [Testing strategy](../development/testing-strategy.md)

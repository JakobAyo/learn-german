---
title: Roadmap
summary: Implementation milestones M0 to M8 from an empty repo to v1.0.0, each with deliverables, tests, CI changes and a done-when check.
status: active
updated: 2026-11-26
---

# Roadmap

## Purpose

Splits v1 (as fixed in [Requirements](requirements.md) and decisions 0002 to 0017) into milestones that each end in a working, tested, released state. Read this to know what to build next and what "done" means for it. How the code is organised is in [Code architecture](../system-design/code-architecture.md); how it is tested is in [Testing strategy](../development/testing-strategy.md); how changes reach `main` and become releases is in [CI and releases](../development/ci-and-releases.md).

## Rules for every milestone

- **CI first.** M0 builds the quality gates before any feature code, so every later line lands through them.
- **Tests ship with the code** in the same pull request. A PR without tests for new behaviour is not done.
- **Work against ports.** M4, M5 and M6 are built and tested against fakes of their neighbours, so they do not wait for each other.
- **Release as features land** ([0023](../decisions/0023-release-as-features-land.md)). Feature PRs accumulate in the release PR; merge it when any milestone's done-when check passes. A 0.x version may contain parts of several parallel tracks, so versions do not map to milestones. 1.0.0 is still forced at M8.
- **Docs and decisions move with the code.** A behaviour change updates its doc; a new choice gets an ADR.
- **Parallel tracks own their files.** M2, M4, M5 and M6 run at the same time in separate worktrees under the ownership rules in [Parallel tracks](../development/parallel-tracks.md) ([0026](../decisions/0026-run-m2-m4-m5-m6-as-parallel-tracks.md)).

## Overview

| # | Milestone | Outcome | Release |
|---|---|---|---|
| M0 | Foundation and CI/CD | Empty package, all quality gates and the release pipeline proven | 0.1.0 (done) |
| M1 | Domain, ports, storage, config | Core types, plug-in interfaces, SQLite with migrations, settings | 0.x |
| M2 | NVV extractor | Text in, correct chunk keys out, guarded by a golden corpus | 0.x |
| M3 | Ingest, `add`, `status`, `reextract` | **First usable tool**: collect sources and see pending chunks | 0.x |
| M4 | Selection | Filter chain, occurrence ranker, cap, occurrence picker | 0.x |
| M5 | Generation | LLM port, Claude adapter, versioned prompt, cache decorator | 0.x |
| M6 | Anki export | AnkiConnect gateway, v1 note types, note builder, tags | 0.x |
| M7 | `sync` | **First cards in Anki**: end-to-end run with partial-failure handling and dry run | 0.x |
| M8 | v1 hardening | README, setup docs, manual release checklist, quality measurement | 1.0.0 |

```
M0 ─► M1 ─┬─► M2 ─► M3 ───────────────┐
          ├─► M4 (fake Anki) ─────────┤
          ├─► M5 (fake LLM) ──────────┼─► M7 ─► M8
          └─► M6 (mocked HTTP) ───────┘
```

---

## M0. Foundation and CI/CD

**Goal:** a repository where a bad change cannot reach `main` and a merged feature becomes a versioned release with a changelog, before any feature exists.

**Deliverables**

- `pyproject.toml`: uv project, `src/learn_german/` layout, console script `learn-german`, dependency group `dev`, tool config for ruff, mypy (`strict = true`), pytest (`--strict-markers`, `--disable-socket`), coverage (branch, `fail_under`) and import-linter. `.python-version` pins 3.12.
- Minimal CLI: `learn-german --version`, read from package metadata.
- `Makefile` with `check` (runs exactly what CI runs), `fmt` and `test`.
- `.pre-commit-config.yaml`: ruff check with fix, ruff format, uv lock check. Slow checks (mypy, tests) stay in `make check` and CI.
- `.gitignore` (`.env`, `*.db`, `.venv/`, caches) and `.env.example` with empty keys only.
- Vendored docs validator in `tools/docs/` (`validate_docs.py`, `build_index.py`, `docs_common.py`, all stdlib), so CI can run it.
- GitHub workflows: `ci.yml`, `pr-title.yml`, `release-please.yml`, plus `release-please-config.json`, `.release-please-manifest.json`, seeded `CHANGELOG.md`, `.github/dependabot.yml` and a short PR template.
- Repository settings applied by hand (listed in [CI and releases](../development/ci-and-releases.md#repository-settings)): branch protection, squash merge only, secret scanning with push protection.
- Docs: `development/setup.md` (clone, `uv sync`, pre-commit install, `make check`).

**Tests:** one CLI smoke test (`--version` exits 0 and prints the package version).

**Decisions:** [0018](../decisions/0018-structure-code-as-ports-and-adapters.md), [0019](../decisions/0019-gate-main-with-ci-checks.md), [0020](../decisions/0020-version-with-conventional-commits-and-release-please.md), [0021](../decisions/0021-settle-m0-build-and-release-mechanics.md).

**Done when**

1. A PR titled `feat: add version flag` runs every CI job green.
2. A deliberately broken PR (type error, failing test, bad PR title) is blocked from merging.
3. Merging opens a release PR whose CI also passes, including the lock check.
4. Merging the release PR creates tag `v0.1.0`, a GitHub Release and a `CHANGELOG.md` entry.
5. `uv tool install git+https://github.com/<owner>/learn-german@v0.1.0` installs a `learn-german` that prints `0.1.0`.

---

## M1. Domain, ports, storage and config

**Goal:** the types and interfaces every later milestone plugs into, and durable local state.

**Deliverables**

- `domain/`: value objects `ChunkKey` (validates the 0011 format), `RunId` (`run-YYYYMMDD-HHMM`), entities `Source`, `Candidate`, `NoteDraft`, `RunSummary`; candidate status that tells apart no notes, one of two notes, and both (required by 0014); error hierarchy `FatalError` / `ItemError`.
- `ports.py`: `Protocol`s for `SourceAdapter`, `ChunkExtractor`, `CandidateFilter`, `Ranker`, `LLMProvider`, `AnkiGateway`, `UnitOfWork`, `Clock`. No implementations beyond the clock.
- `adapters/storage/sqlite/`: numbered `.sql` migrations shipped as package data, applied in order and tracked with `PRAGMA user_version`; repositories for sources, candidates and the LLM cache; a `UnitOfWork` that commits or rolls back one transaction.
- `config.py`: settings with precedence flag > environment > `~/.config/learn-german/config.toml` > default (R12, R25); XDG paths via `platformdirs`; `.env` support; hint language validated only when generation needs it (R16).
- Docs: `data/data-model.md` (tables, columns, statuses).

**Tests**

- Unit: `ChunkKey` valid and invalid cases (parametrised), `RunId` with a fixed clock.
- Migrations: an empty database reaches the latest version; running again is a no-op; every migration applies to the previous version.
- Repository contract suite: round trips, a source is unique by URL and by content hash, candidate upsert, unit of work rolls back on exception.
- Config: precedence table as one parametrised test; no test touches the real home directory.

**Decision to record:** settings library. Recommendation: `pydantic-settings`, since the Anthropic SDK already pulls in pydantic and M5 uses it to validate LLM output. Keep pydantic out of `domain/`.

**Done when:** the full domain model can be stored and loaded through the unit of work, and import-linter proves `domain/` imports nothing from adapters or third-party I/O libraries.

---

## M2. NVV extractor

**Goal:** German text in, Nomen-Verb-Verbindungen with correct keys, sentence and context window out (R8, R10, 0011).

**Deliverables**

- Split into three parts so the hard logic is testable without spaCy:
  - `parse`: loads `de_core_news_lg` once, lazily; batches with `nlp.pipe`; converts spaCy tokens into a small `TokenView` dataclass (text, lemma, POS, dependency, head).
  - `match`: finds light verb plus noun object or prepositional object on `TokenView`s.
  - `keys`: a pure function from matched `TokenView`s to `ChunkKey`, applying contraction expansion, reflexive `sich`, separable prefixes, and the spelling-variant table.
- Data files loaded through `importlib.resources`: `light_verbs.txt`, `spelling_variants.tsv`.
- ~~Citation form for the `Chunk` field~~: settled before the parallel tracks started; the LLM returns it in M5 ([0028](../decisions/0028-let-the-llm-supply-the-citation-form.md)).
- Context window: the sentence plus one sentence either side.
- Extractor registry keyed by name, filled in the composition root.

**Decision recorded:** the spaCy model is the optional extra `model` holding the pinned wheel URL ([0027](../decisions/0027-settle-shared-dependencies-before-parallel-tracks.md)), so `uv tool install 'learn-german[model] @ git+…'` gets everything and fast CI jobs skip the 500 MB download.

**Tests**

- Unit (no spaCy): key builder on hand-built `TokenView`s, covering every row of the 0011 table, negation and articles dropped, and variant mapping.
- NLP (`@pytest.mark.nlp`, real model): every 0011 row in synthetic sentences with hard word order: separated prefix (*stellte … zur Verfügung*), perfect tense (*hat … getroffen*), subordinate clause, negation.
- Golden corpus: about 50 hand-written synthetic sentences with expected keys. The test computes precision and recall and fails if either drops below the recorded baseline, so a change to the light-verb list or matcher cannot quietly make extraction worse.
- Data files: lowercase, no duplicates, sorted.

**CI change:** add the `nlp` job, with the model wheel cached by uv.

**Done when:** the 0011 table passes against the real model and the golden-corpus baseline is recorded.

---

## M3. Ingest, `add`, `status`, `reextract`

**Goal:** the first usable version. The owner can collect articles and files and see what is pending (R4 to R6, 0013, 0017).

**Deliverables**

- `LocalFileSource`: `.txt`, UTF-8, whitespace normalised, SHA-256 of the normalised text as content hash.
- `NewsUrlSource`: `httpx` with timeouts and a generic User-Agent, robots.txt checked before the article is fetched, only the given URL, `trafilatura` main-text extraction. 401, 402 and 403 responses and too-short text raise a clear error that points to the `.txt` fallback.
- Adapter selection: each adapter answers `can_handle(ref)`; the first match wins.
- Use cases: `AddSources` (skip known sources unless `--force`, ingest, extract and store one source per unit of work, per-source report, non-zero exit if any failed), `ShowStatus`, `Reextract` (the four 0017 rules).
- CLI commands `add` (with `--from`), `status` and `reextract` as thin wrappers; formatting lives in a presenter module.

**Tests**

- News source against `httpx.MockTransport`: robots.txt disallow (the article URL is never requested), 403, paywall-like short text, timeout, success with a synthetic HTML fixture.
- Local file: empty file, invalid encoding.
- `AddSources` with fakes: dedupe by URL and by hash, `--force`, one failing source does not stop the rest, exit code.
- `Reextract`: the four cases (kept, new, vanished pending, vanished with notes) as one parametrised test.
- CLI via typer's `CliRunner`: `add` on a fixture file prints counts; `--from` reads a list; exit codes.

**Done when:** `learn-german add` on real articles (manually) and on fixtures (in CI) stores candidates, and `status` lists them.

---

## M4. Selection

**Goal:** turn pending candidates into the ranked, capped list of chunks to generate (R11 to R14).

**Deliverables**

- `FilterChain` (composite of `CandidateFilter`s) with the v1 filter `AlreadyInDeckFilter`, which asks the `AnkiGateway` port for existing keys per note type and keeps only the missing note types per chunk.
- `OccurrenceRanker`: counts occurrences per key in SQL, most frequent first, ties broken deterministically.
- Cap as a pure function.
- `OccurrencePicker` strategy that chooses which sentence feeds the cards. This closes the open question in [Pipeline](../system-design/pipeline.md). Recommendation: the shortest sentence within a word range, most recent on ties. Record it as an ADR.
- `status` reuses the same ranker for its top-pending list.

**Tests:** pure unit tests with a fake gateway: chunk with both notes dropped, chunk with one note keeps only the missing type, ranking ties stable, cap of 0 and cap larger than the candidate count, picker choices.

**Done when:** given fixtures, selection returns the expected chunks and missing note types in the expected order.

---

## M5. Generation

**Goal:** one LLM call per chunk returns validated card content, never paid for twice (R15 to R17, 0004, 0012).

**Deliverables**

- `CardRequest` and `CardContent` exist in `domain/models.py` and are frozen while the tracks run ([0026](../decisions/0026-run-m2-m4-m5-m6-as-parallel-tracks.md)). `CardContent` holds citation form, shortened sentence, verbal-style rewrite, translation and meaning, validated by a pydantic model at the adapter boundary.
- Prompt as a template file plus `PROMPT_VERSION`; rendering is a pure function.
- `AnthropicProvider`: Anthropic SDK, structured JSON output against the `CardContent` schema, model from config (default `claude-opus-5-5`), SDK retries. Authentication failure maps to `FatalError`; invalid output maps to `ItemError`.
- `CachingProvider` decorator wrapping any provider, keyed by hash of provider, model, prompt version and canonical request. Every future provider gets caching for free.
- Cheap sanity checks beyond the schema: answer contains the chunk's noun, shortened sentence within the word range, meaning is one line. A failure is an `ItemError`, so the chunk stays pending. This is the first cheap guard for the quality question in [0005](../decisions/0005-push-cards-automatically-with-tagging-and-dry-run.md).
- `FakeProvider` for tests.
- Optional `tools/eval/` script that runs the prompt on a handful of chunks for manual review. Never run in CI.

**Tests**

- Prompt golden file. A second test stores the template's hash per `PROMPT_VERSION` and fails if the template changes without a version bump, which would otherwise serve stale cache entries.
- Cache decorator: hit, miss, and a key change for each key component.
- Anthropic adapter against `httpx.MockTransport` (the SDK accepts a custom HTTP client): success, malformed JSON, schema violation, 401, server errors after retries.
- Sanity checks as a parametrised table.

**Done when:** a fake chunk turns into validated `CardContent` through the real adapter with mocked HTTP, and a second identical call makes no HTTP request.

---

## M6. Anki export

**Goal:** the tool can create its deck and note types and add tagged notes through AnkiConnect (R19 to R22, [Note types](../learning-design/note-types.md)).

**Deliverables**

- `AnkiConnectClient`: the JSON request envelope, AnkiConnect's `error` field, connection refused mapped to `AnkiUnavailable` (fatal), version check.
- `NoteTypeSpec` for `learn-german-transformation-v1` and `learn-german-translation-v1`: name, fields in order with `ChunkKey` first, templates and CSS as package files.
- `AnkiConnectGateway` implementing the port: `ensure_setup()` creates the deck and missing note types and fails clearly if an existing type's fields differ (a migration is needed); `existing_keys(note_type)`; `add_notes(drafts)`.
- `NoteBuilder`: pure function from `CardContent` and candidate to the two `NoteDraft`s; tag builder (`learn-german`, `provider::…`, `model::…`, `run::…`).
- `FakeAnkiGateway`: an in-memory deck that passes the same contract tests as the real gateway.
- Docs: `integrations/ankiconnect.md` (setup, actions used, failure modes).

**Tests**

- Client against `httpx.MockTransport`: request shape, error field, connection refused.
- Gateway contract suite run against the fake, and against the real gateway over a mocked client.
- Frozen spec test: v1 field names and order are asserted literally, so a field change fails CI until a `-v2` type and migration exist.
- Note builder and tags as unit tests; card templates as golden files.
- Manual smoke test against a throwaway Anki profile, written down in the release checklist.

**Done when:** against a real throwaway Anki profile, `ensure_setup()` is idempotent and two pushed notes render as specified.

---

## M7. `sync`

**Goal:** the first real cards. One command runs filter, rank, cap, generate and push with the failure rules from 0014 (R12, R21 to R23a).

**Deliverables**

- `SyncService` use case:
  1. Preflight before spending money: hint language set, API key present, Anki reachable and set up. Each failure is fatal. In `--dry-run`, an unreachable Anki becomes a warning and deduplication is skipped.
  2. Select (M4), then for each chunk in its own unit of work: generate (cached), build notes, push only the missing notes, update status.
  3. `ItemError`: record the error on the candidate and continue. `FatalError`: stop at once.
  4. Print the run summary. Exit codes: 0 all ok, 1 some items failed, 2 fatal or usage error.
- `RunId` from the injected clock and attached as a tag.
- `--dry-run` prints the notes that would be added, with LLM output cached.
- Composition root `bootstrap.py` builds the real object graph from settings; tests pass overrides.

**Tests (end to end through the CLI with fakes)**

- Happy path: N chunks become 2N notes with the right tags.
- Cap and ranking order respected.
- Dry run makes no `add_notes` call; a following real sync makes no new LLM call.
- One chunk fails generation: the others are pushed, the failed one stays pending with its error, exit 1.
- The second note's push fails: the next sync creates only that note.
- Anki unreachable: stops before any LLM call, exit 2.
- Missing hint language: refuses before any call.
- Running sync twice creates no duplicates.

**Done when:** on the owner's machine, `add` then `sync --cap 3` puts 6 correct notes into Anki, and a repeated `sync` adds nothing.

---

## M8. v1 hardening and 1.0.0

**Goal:** a v1 the owner can reinstall from scratch and trust.

**Deliverables**

- `README.md`: what and why, install from a tag with the model extra, Anki and AnkiConnect setup, configuration, the `add` / `sync` workflow.
- Docs: `development/release-checklist.md` (manual end-to-end against real Anki and the real API), `integrations/claude-api.md`.
- Review every error message for a clear next step; add `--verbose` logging.
- Quality measurement: run on about five real articles, grade 20 cards, record the error rate in `research/`. This answers the open question in [Requirements](requirements.md) and decides whether 0005 needs revisiting.
- Release 1.0.0 with a `Release-As: 1.0.0` commit footer.

**Done when:** a fresh install by following only the README produces cards, and the release checklist passes.

---

## After v1

Not planned in detail. Each item plugs into a seam from the Deferred table in [Requirements](requirements.md): more source adapters, more extractors, a known-item filter, more ranking signals, more LLM providers, audio. Each one becomes a `feat:` PR and a minor release.

## Related

- [Requirements](requirements.md)
- [Code architecture](../system-design/code-architecture.md)
- [Testing strategy](../development/testing-strategy.md)
- [CI and releases](../development/ci-and-releases.md)
- [Coding conventions](../development/coding-conventions.md)

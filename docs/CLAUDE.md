---
title: learn-german documentation
summary: Index of the documentation tree. Start here to find which folder holds what.
---

# learn-german documentation

A personal command-line tool that mines German source material (news articles, local files) for chunks, chiefly Nomen-Verb-Verbindungen, and pushes sentence-transformation and translation-prompt cards into Anki for spaced repetition. Its goal is to move a B2 learner towards C1 by widening the words they actually use and improving how they build sentences, rather than by adding passive word lists.

## How to use this index

- Each folder below covers exactly one concern. Read the folder's `CLAUDE.md` first; it states what belongs there and lists every file with a one-line summary.
- Open a file only when its summary matches what you need. Do not read the whole tree.
- Every decision that shaped this project is recorded in `decisions/` as a numbered record. Check there before changing an established approach.

## Conventions

- Folder and file names are kebab-case. Decision records are `NNNN-short-title.md`.
- Every document starts with frontmatter: `title`, `summary`, `status` (draft, active, deprecated, superseded), `updated` (YYYY-MM-DD).
- The index sections between the `docs-index` markers are generated. Edit the text outside them; regenerate the rest with `build_index.py`.

<!-- docs-index:start -->

## Index

### [data/](data/CLAUDE.md)

Input sources, frequency lists, known-words store and the extracted-item data model.

- [Data model](data/data-model.md) — SQLite tables, columns and constraints, how chunk status is derived from pushed notes, and how schema migrations are numbered and applied.

### [decisions/](decisions/CLAUDE.md)

Numbered decision records (ADRs). Why the project is the way it is, one decision per file.

- [Adopt a concern-based documentation structure](decisions/0001-adopt-documentation-structure.md) — Documentation is split into one folder per concern, each indexed by a CLAUDE.md, with decisions recorded as numbered records.
- [Build a single-user Python CLI in a public repository](decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md) — The tool is a Python 3.12+ CLI managed with uv, used by one person, published as a public repo with nothing personal in it.
- [Push notes live through AnkiConnect into a tool-owned deck](decisions/0003-push-notes-live-through-ankiconnect.md) — Notes go into the running Anki desktop app through AnkiConnect, into a deck and versioned note types the tool owns, instead of .apkg files.
- [Generate card content through a pluggable LLM provider, Claude API first](decisions/0004-generate-card-content-through-a-pluggable-llm-provider.md) — Translations and model answers come from an LLM provider interface; the Claude API is the first adapter, with claude -p and DeepSeek addable later.
- [Push cards automatically, with tagging and dry run as safeguards](decisions/0005-push-cards-automatically-with-tagging-and-dry-run.md) — There is no review step; generated notes go straight to Anki, each tagged with provider, model and run ID, and --dry-run previews a run.
- [Use transformation and translation-prompt cards, not chunk cloze](decisions/0006-use-transformation-and-translation-prompt-cards.md) — v1 builds two production card types, sentence transformation and translation prompt, and drops the chunk cloze proposed in the DeepSeek chat.
- [Keep local state in SQLite](decisions/0007-keep-local-state-in-sqlite.md) — A local SQLite database stores processed sources, all extracted candidates and cached LLM output, outside the repository.
- [Make chunk extractors and source adapters pluggable, starting with NVV](decisions/0008-make-chunk-extractors-pluggable-starting-with-nvv.md) — Extraction and ingest are plug-in interfaces; v1 ships the Nomen-Verb-Verbindung extractor and the news-URL and local-file sources.
- [Deduplicate by chunk key, rank candidates and cap new notes per run](decisions/0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md) — Chunks already in the deck are skipped by lemma key; a configurable cap limits new notes per run, ranked by occurrences in the learner's sources.
- [License the code under MIT](decisions/0010-license-the-code-under-mit.md) — The public repository is released under the MIT licence, the shortest permissive option.
- [Normalise NVV chunk keys as noun, preposition, verb](decisions/0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md) — An NVV's permanent key is the lemmas of noun, preposition, optional sich, and verb, joined by |, without articles or negation.
- [Make both cards practise the chunk, two notes per chunk](decisions/0012-make-both-cards-practise-the-chunk.md) — Both cards drill the chunk on a shortened sentence; one note of each type per chunk, and the cap counts chunks.
- [Fetch articles politely, without bypassing paywalls](decisions/0013-fetch-articles-politely-without-bypassing-paywalls.md) — The news-URL adapter fetches only the given URL, respects robots.txt and fails clearly on paywalls; a local .txt file is the fallback.
- [Keep progress when a run fails partway](decisions/0014-keep-progress-when-a-run-fails-partway.md) — A failing candidate stays pending with its error recorded, the run continues, and a summary lists failures; the next run retries them.
- [Set v1 run defaults, Claude Opus 5.5, ten chunks, required hint language](decisions/0015-set-v1-run-defaults.md) — The default model is Claude Opus 5.5, the default cap is 10 chunks per run, and there is no default hint language; the user must set one.
- [Use standard Python tooling for CLI, types, fetching and NLP](decisions/0016-use-standard-python-tooling.md) — typer for the CLI, mypy --strict, httpx and trafilatura for fetching, spaCy de_core_news_lg, a light-verb data file, timestamp run IDs and a learn-german deck.
- [Split the CLI into add and sync, with extraction at add time](decisions/0017-split-the-cli-into-add-and-sync.md) — add fetches and extracts sources into SQLite; sync ranks, deduplicates, generates and pushes up to the cap; reextract rebuilds candidates from stored text.
- [Structure the code as ports and adapters with a composition root](decisions/0018-structure-code-as-ports-and-adapters.md) — Pure domain, use cases against Protocol ports, one adapter per external system, wired in one composition root; layering enforced by import-linter.
- [Gate main with required CI checks and branch protection](decisions/0019-gate-main-with-ci-checks.md) — main accepts only squash-merged PRs that pass lint, lock, mypy, import-linter, pytest with coverage, NLP tests, docs validation and a PR-title check.
- [Version with Conventional Commits and release-please](decisions/0020-version-with-conventional-commits-and-release-please.md) — Conventional Commit PR titles drive SemVer; release-please keeps a release PR that bumps pyproject.toml and CHANGELOG.md and tags on merge.
- [Settle M0 build and release mechanics](decisions/0021-settle-m0-build-and-release-mechanics.md) — uv_build backend, uv.lock refreshed by the release workflow, pre-commit on the locked ruff, and layer stubs so import-linter enforces 0018 now.
- [Keep a long-lived develop branch](decisions/0022-keep-a-long-lived-develop-branch.md) — develop is a protected integration branch that survives merges; after each squash merge into main, main is merged back into develop.
- [Release as features land, not once per milestone](decisions/0023-release-as-features-land.md) — M2 to M6 run as parallel tracks after M1, so 0.x versions count up as features merge and no longer map to milestones; 1.0.0 stays tied to M8.
- [Read settings with pydantic-settings, layered flag, environment, .env and TOML](decisions/0024-read-settings-with-pydantic-settings.md) — pydantic-settings layers flags, LEARN_GERMAN_ variables, .env and config.toml; unknown TOML keys fail and the hint language is an ISO 639 code.
- [Track note progress per chunk key, not per occurrence](decisions/0025-track-note-progress-per-chunk-key.md) — Candidates are occurrences without status; pushed notes and errors are stored per chunk key, and pending, partial or done is derived from them.
- [Run M2, M4, M5 and M6 as parallel tracks with file ownership](decisions/0026-run-m2-m4-m5-m6-as-parallel-tracks.md) — Four agents build M2, M4, M5 and M6 at once in worktrees; each track owns fixed files, shared contracts are frozen, and tracks merge into develop.
- [Settle runtime dependencies up front, httpx2 and the spaCy model extra](decisions/0027-settle-shared-dependencies-before-parallel-tracks.md) — anthropic, httpx2 and spaCy 3.8 are added before the tracks; httpx2 replaces httpx as the SDK uses it; the spaCy model is an optional extra.
- [Let the LLM supply the citation form of a chunk](decisions/0028-let-the-llm-supply-the-citation-form.md) — The Chunk field comes from the LLM as CardContent.citation_form, not the extractor, because the citation article is not in the parse.

### [development/](development/CLAUDE.md)

Local setup, dependencies and NLP models, and how to run the extractor.

- [CI and releases](development/ci-and-releases.md) `[draft]` — CI jobs that gate main, repository settings, the Conventional Commits PR-title rule, and how release-please produces versions, tags and CHANGELOG.md.
- [Coding conventions](development/coding-conventions.md) `[draft]` — Typing, naming, error handling, I/O boundaries, configuration and pull-request rules that every change follows.
- [Configuration](development/configuration.md) — Every setting with its default, environment variable and TOML key, where config.toml and .env are read from, and the order in which sources override each other.
- [Parallel tracks](development/parallel-tracks.md) — File ownership of the parallel tracks M2, M4, M5 and M6, frozen files, reserved decision numbers, and the path from worktree to develop and main.
- [Local setup](development/setup.md) — Clone, install with uv, enable pre-commit and run make check; what each make target runs and how to install a released version.
- [Testing strategy](development/testing-strategy.md) `[draft]` — Test layers from pure unit to manual release checks, fakes and contract tests, the no-network and synthetic-fixture rules, and coverage targets.

### [integrations/](integrations/CLAUDE.md)

External systems: Anki, translation, audio and any LLM; how each is called and fails.

- (empty)

### [learning-design/](learning-design/CLAUDE.md)

Card types, what each trains, Anki deck and note-type layout, review settings.

- [Note types](learning-design/note-types.md) — Deck, the two v1 note types and their fields, card fronts and backs, and tags; fields are hard to change once notes exist.

### [product/](product/CLAUDE.md)

Learning goals, scope, non-goals and roadmap of the extractor.

- [Learning goals](product/learning-goals.md) — B2 to C1 goal, the two core weaknesses (word finding, error-free sentences) and why Anki is the study channel.
- [Requirements](product/requirements.md) — Functional and non-functional requirements, scope, non-goals and deferred features, agreed before implementation starts.
- [Roadmap](product/roadmap.md) — Implementation milestones M0 to M8 from an empty repo to v1.0.0, each with deliverables, tests, CI changes and a done-when check.

### [research/](research/CLAUDE.md)

Experiments, evaluations and summaries of outside advice that inform decisions.

- [DeepSeek chat: chunks and sentence transformation](research/deepseek-chat-advice.md) — Summary and critique of the DeepSeek advice: mine Nomen-Verb-Verbindungen with spaCy, cloze and transformation cards via genanki.

### [system-design/](system-design/CLAUDE.md)

Extraction pipeline: ingest, NLP processing, filtering and ranking, card generation, export.

- [Code architecture](system-design/code-architecture.md) `[draft]` — Ports-and-adapters layout of the Python package, the dependency rule, every port with its v1 adapter and fake, and the patterns used where.
- [Pipeline](system-design/pipeline.md) — Stages from source to Anki note, which command (add or sync) owns each, and what each stage reads from and writes to SQLite.

<!-- docs-index:end -->

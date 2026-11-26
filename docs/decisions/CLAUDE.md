---
title: Decisions
summary: Numbered decision records (ADRs). Why the project is the way it is, one decision per file.
---

# Decisions

Every non-trivial choice that shaped this project gets one record here. Records are append-only. A changed decision gets a new record that supersedes the old one; the old record stays, with its status set to `superseded`.

## What belongs here

- Architecture and technology choices, and the alternatives that were rejected.
- Process and convention decisions (branching model, review rules, release cadence).
- Anything a future reader might otherwise undo because they do not know why it was done.

## What does not belong here

- Descriptions of how the system works today. Those go in the concern folder they belong to, and the record links to them.
- Task lists, meeting notes, or status updates.

## How to add a record

Use the helper, which picks the next number and writes valid frontmatter:

```bash
python3 ~/.claude/skills/docs-architect/scripts/new_doc.py --docs-root docs --adr --title "Use PostgreSQL for primary storage"
```

Or copy this template into `NNNN-short-title.md` by hand:

```markdown
---
title: Short imperative title
summary: One line stating the decision and its main reason.
status: active
updated: YYYY-MM-DD
---

# Short imperative title

## Context

What situation or problem forced a choice. Constraints that mattered.

## Decision

What was decided, stated plainly.

## Alternatives considered

- Option A: why it was rejected.
- Option B: why it was rejected.

## Consequences

What becomes easier, what becomes harder, what must be revisited later.
```

Status meanings for records: `draft` = proposed and not yet agreed, `active` = accepted and in force, `deprecated` = no longer applies and nothing replaced it, `superseded` = replaced by a newer record (name it in the body).

<!-- docs-index:start -->

## Contents

- [Adopt a concern-based documentation structure](0001-adopt-documentation-structure.md) — Documentation is split into one folder per concern, each indexed by a CLAUDE.md, with decisions recorded as numbered records.
- [Build a single-user Python CLI in a public repository](0002-build-a-single-user-python-cli-in-a-public-repo.md) — The tool is a Python 3.12+ CLI managed with uv, used by one person, published as a public repo with nothing personal in it.
- [Push notes live through AnkiConnect into a tool-owned deck](0003-push-notes-live-through-ankiconnect.md) — Notes go into the running Anki desktop app through AnkiConnect, into a deck and versioned note types the tool owns, instead of .apkg files.
- [Generate card content through a pluggable LLM provider, Claude API first](0004-generate-card-content-through-a-pluggable-llm-provider.md) — Translations and model answers come from an LLM provider interface; the Claude API is the first adapter, with claude -p and DeepSeek addable later.
- [Push cards automatically, with tagging and dry run as safeguards](0005-push-cards-automatically-with-tagging-and-dry-run.md) — There is no review step; generated notes go straight to Anki, each tagged with provider, model and run ID, and --dry-run previews a run.
- [Use transformation and translation-prompt cards, not chunk cloze](0006-use-transformation-and-translation-prompt-cards.md) — v1 builds two production card types, sentence transformation and translation prompt, and drops the chunk cloze proposed in the DeepSeek chat.
- [Keep local state in SQLite](0007-keep-local-state-in-sqlite.md) — A local SQLite database stores processed sources, all extracted candidates and cached LLM output, outside the repository.
- [Make chunk extractors and source adapters pluggable, starting with NVV](0008-make-chunk-extractors-pluggable-starting-with-nvv.md) — Extraction and ingest are plug-in interfaces; v1 ships the Nomen-Verb-Verbindung extractor and the news-URL and local-file sources.
- [Deduplicate by chunk key, rank candidates and cap new notes per run](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md) — Chunks already in the deck are skipped by lemma key; a configurable cap limits new notes per run, ranked by occurrences in the learner's sources.
- [License the code under MIT](0010-license-the-code-under-mit.md) — The public repository is released under the MIT licence, the shortest permissive option.
- [Normalise NVV chunk keys as noun, preposition, verb](0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md) — An NVV's permanent key is the lemmas of noun, preposition, optional sich, and verb, joined by |, without articles or negation.
- [Make both cards practise the chunk, two notes per chunk](0012-make-both-cards-practise-the-chunk.md) — Both cards drill the chunk on a shortened sentence; one note of each type per chunk, and the cap counts chunks.
- [Fetch articles politely, without bypassing paywalls](0013-fetch-articles-politely-without-bypassing-paywalls.md) — The news-URL adapter fetches only the given URL, respects robots.txt and fails clearly on paywalls; a local .txt file is the fallback.
- [Keep progress when a run fails partway](0014-keep-progress-when-a-run-fails-partway.md) — A failing candidate stays pending with its error recorded, the run continues, and a summary lists failures; the next run retries them.
- [Set v1 run defaults, Claude Opus 5.5, ten chunks, required hint language](0015-set-v1-run-defaults.md) — The default model is Claude Opus 5.5, the default cap is 10 chunks per run, and there is no default hint language; the user must set one.
- [Use standard Python tooling for CLI, types, fetching and NLP](0016-use-standard-python-tooling.md) — typer for the CLI, mypy --strict, httpx and trafilatura for fetching, spaCy de_core_news_lg, a light-verb data file, timestamp run IDs and a learn-german deck.
- [Split the CLI into add and sync, with extraction at add time](0017-split-the-cli-into-add-and-sync.md) — add fetches and extracts sources into SQLite; sync ranks, deduplicates, generates and pushes up to the cap; reextract rebuilds candidates from stored text.
- [Structure the code as ports and adapters with a composition root](0018-structure-code-as-ports-and-adapters.md) — Pure domain, use cases against Protocol ports, one adapter per external system, wired in one composition root; layering enforced by import-linter.
- [Gate main with required CI checks and branch protection](0019-gate-main-with-ci-checks.md) — main accepts only squash-merged PRs that pass lint, lock, mypy, import-linter, pytest with coverage, NLP tests, docs validation and a PR-title check.
- [Version with Conventional Commits and release-please](0020-version-with-conventional-commits-and-release-please.md) — Conventional Commit PR titles drive SemVer; release-please keeps a release PR that bumps pyproject.toml and CHANGELOG.md and tags on merge.
- [Settle M0 build and release mechanics](0021-settle-m0-build-and-release-mechanics.md) — uv_build backend, uv.lock refreshed by the release workflow, pre-commit on the locked ruff, and layer stubs so import-linter enforces 0018 now.
- [Keep a long-lived develop branch](0022-keep-a-long-lived-develop-branch.md) — develop is a protected integration branch that survives merges; after each squash merge into main, main is merged back into develop.
- [Release as features land, not once per milestone](0023-release-as-features-land.md) — M2 to M6 run as parallel tracks after M1, so 0.x versions count up as features merge and no longer map to milestones; 1.0.0 stays tied to M8.
- [Read settings with pydantic-settings, layered flag, environment, .env and TOML](0024-read-settings-with-pydantic-settings.md) — pydantic-settings layers flags, LEARN_GERMAN_ variables, .env and config.toml; unknown TOML keys fail and the hint language is an ISO 639 code.
- [Track note progress per chunk key, not per occurrence](0025-track-note-progress-per-chunk-key.md) — Candidates are occurrences without status; pushed notes and errors are stored per chunk key, and pending, partial or done is derived from them.
- [Run M2, M4, M5 and M6 as parallel tracks with file ownership](0026-run-m2-m4-m5-m6-as-parallel-tracks.md) — Four agents build M2, M4, M5 and M6 at once in worktrees; each track owns fixed files, shared contracts are frozen, and tracks merge into develop.
- [Settle runtime dependencies up front, httpx2 and the spaCy model extra](0027-settle-shared-dependencies-before-parallel-tracks.md) — anthropic, httpx2 and spaCy 3.8 are added before the tracks; httpx2 replaces httpx as the SDK uses it; the spaCy model is an optional extra.
- [Let the LLM supply the citation form of a chunk](0028-let-the-llm-supply-the-citation-form.md) — The Chunk field comes from the LLM as CardContent.citation_form, not the extractor, because the citation article is not in the parse.
- [Match NVVs in ranked tiers on the dependency parse, without a noun lexicon](0029-match-nvvs-in-ranked-tiers-without-a-noun-lexicon.md) — A light verb's NVV is the first non-empty tier of cvc phrase or variant, bare object, last bare PP, other object; no list of NVV nouns is used.
- [Keep a verb's own separable prefix in the key, and list light verbs by full infinitive](0030-keep-a-verbs-own-separable-prefix-in-the-key.md) — The verb in a chunk key includes its own separated prefix (nahm Kontakt auf → kontakt|aufnehmen); the light-verb list holds full infinitives such as aufnehmen.
- [Guard extraction quality with a golden-corpus baseline](0031-guard-extraction-with-a-golden-corpus-baseline.md) — Hand-written sentences with expected keys are scored for micro-averaged precision and recall; the nlp test fails below the baseline stored next to the corpus.
- [Feed the cards from the shortest sentence of at least ten words](0032-feed-cards-from-the-shortest-sentence-of-ten-words.md) — Of a chunk's occurrences, the picker takes the shortest sentence with at least ten words, else the longest; ties go to the most recent occurrence.
- [Count a note as present if the local record or Anki has it](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md) — A note kind is needed only if neither pushed_notes nor the Anki deck has it, so locally done chunks skip Anki and a note deleted in Anki stays deleted.
- [Rank partial chunks first, then by occurrences, ties by key](0034-rank-partial-chunks-first-then-by-occurrences.md) — OccurrenceRanker puts chunks that already have one note first, then orders by occurrence count, most first, and breaks ties by the chunk key.
- [Version the card prompt as a template file with a pinned hash](0035-version-the-card-prompt-as-a-template-with-a-pinned-hash.md) — The card prompt is a template file beside the LLM adapters with a pure renderer; PROMPT_VERSION is in every cache key, and a test pins its hash.
- [Check card content cheaply, then cache it per request in its own transaction](0036-check-card-content-then-cache-it-in-its-own-transaction.md) — CheckedProvider turns clearly wrong content into a GenerationError; CachingProvider wraps it, keyed by a request hash, in its own transactions.
- [Call Claude with a JSON-schema output format and split API errors into fatal and item](0037-call-claude-with-a-json-schema-and-split-errors-into-fatal-and-item.md) — One Messages call with a JSON-schema output at medium effort, no refusal fallback; rejected access is fatal, failures after retries are item errors.
- [Create missing note types and check only their fields](0038-create-missing-note-types-and-check-only-their-fields.md) — ensure_setup creates the deck and missing note types from package template files, fails if an existing type's fields differ, and never edits an existing type.
- [Read existing keys per note type across the whole collection](0039-read-existing-keys-per-note-type-across-the-collection.md) — existing_keys counts every note of the tool's note type wherever it is, not only in the deck, so it agrees with Anki's own duplicate check on add.
- [Add notes one call each, escape field values, and split AnkiConnect errors into fatal and item](0040-add-notes-one-call-each-and-split-ankiconnect-errors.md) — One addNote call per note so a rejection is attributable, field values HTML-escaped, unreachable or failing setup is fatal, a rejected note is a PushError.

<!-- docs-index:end -->

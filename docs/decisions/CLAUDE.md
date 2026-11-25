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

<!-- docs-index:end -->

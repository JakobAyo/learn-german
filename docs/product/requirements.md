---
title: Requirements
summary: Functional and non-functional requirements, scope, non-goals and deferred features, agreed before implementation starts.
status: active
updated: 2026-11-27
---

# Requirements

## Purpose

States what the extractor must do and the constraints it must respect, so that the architecture does not need a major refactor when a later feature arrives. Each requirement traces back to [Learning goals](learning-goals.md); the decisions behind them are linked inline. Read this before designing or changing a pipeline stage.

## Users and form factor

- **R1. Single user.** Only the owner runs the tool. There are no accounts or per-user settings. ([0002](../decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md))
- **R2. CLI on the owner's machine.** Commands are started manually from the command line. Nothing runs on a schedule, and no server is involved.
- **R2a. Two-step workflow.** `add` fetches and extracts sources into the local database; `sync` selects, generates and pushes cards. Many sources can be added before one `sync`. `status` shows what is pending and `reextract` rebuilds candidates from stored text. A "run" in these requirements means one `sync`. ([0017](../decisions/0017-split-the-cli-into-add-and-sync.md), [Pipeline](../system-design/pipeline.md))
- **R3. Public repository.** The code is public on GitHub. The repo must not contain anything personal: no API keys, no Anki profile paths, no personal config, no mined sentences, no copyrighted source text. All of that lives outside the repo (see R20).

## Inputs

- **R4. Sources.** The ingest layer must accept:
  - news article URLs, with the main text extracted from the HTML. Only the given URL is fetched, robots.txt is respected and paywalls are never bypassed; a blocked page fails clearly and points to the `.txt` fallback ([0013](../decisions/0013-fetch-articles-politely-without-bypassing-paywalls.md));
  - local files (at least `.txt`; other formats such as `.srt`, `.epub` and `.pdf` are added later through the same interface).
- **R5. Pluggable ingest.** Each source kind is one adapter behind a common interface that yields plain text plus source metadata (URL or path, title, fetch time). New kinds such as YouTube subtitles or the learner's own writing must be addable without changes downstream.
- **R6. No reprocessing.** A source that was already processed is recognised by `add` (by URL or content hash) and skipped unless the user passes `--force`. A source that fails is reported and skipped without stopping the other sources.

## Extraction

- **R7. Chunks, not words.** The unit of extraction is a multi-word chunk. ([0008](../decisions/0008-make-chunk-extractors-pluggable-starting-with-nvv.md))
- **R8. Nomen-Verb-Verbindungen first.** v1 extracts only Nomen-Verb-Verbindungen, using the spaCy dependency parse and a light-verb whitelist (see [DeepSeek chat advice](../research/deepseek-chat-advice.md)).
- **R9. Pluggable extractors.** Chunk kinds are plug-ins behind a common interface. Planned later kinds: formal prepositions (*anlässlich*, *bezüglich*, *gemäß*), verbs with fixed prepositions (*sich beschäftigen mit*), and collocations and idioms.
- **R10. What each mined item stores:** the chunk's normalised lemma key (format in [0011](../decisions/0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)), its kind, the source sentence, the surrounding sentences (context window), and the source reference (URL or file path, title). The full parse is not stored.

## Selection

- **R11. Deduplication by chunk key.** A note is created only if no note of the same note type in the tool's deck has that lemma key, so a re-run or a new article never creates a second note for the same chunk, and a chunk missing some of its notes gets just those. ([0009](../decisions/0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md), [0012](../decisions/0012-make-both-cards-practise-the-chunk.md))
- **R12. Per-run cap.** The maximum number of new chunks per `sync` (each producing one note) is configurable through the `--cap` flag, overriding an environment variable, overriding a default of 10. The cap also bounds LLM cost; there is no separate spending limit. ([0015](../decisions/0015-set-v1-run-defaults.md))
- **R13. Ranking.** When candidates exceed the cap, the highest ranked go first. v1 ranks by how often a chunk occurs across the learner's own processed sources (counted from the local database), most frequent first. No external frequency list or curated NVV list is used. The ranker is pluggable, so such lists can be added later as extra signals if the results disappoint.
- **R14. Known-item filtering is deferred.** v1 does not filter out chunks the learner already knows, apart from R11. The pipeline keeps a filter stage between extraction and ranking, so a filter can be added later (from the Anki collection, a local known list or a frequency cut-off) without restructuring.

## Card generation

- **R15. Card types.** v1 produces one production card type, one note per chunk; chunk cloze is not built. It is built on the source sentence shortened by the LLM to the clause around the chunk. ([0006](../decisions/0006-use-transformation-and-translation-prompt-cards.md), [0012](../decisions/0012-make-both-cards-practise-the-chunk.md), [0049](../decisions/0049-drop-the-translation-card-and-the-hint-language.md))
  - **Transformation:** given the sentence with the NVV, rewrite it in verbal style without the NVV ([0050](../decisions/0050-show-the-nvv-sentence-on-the-front-of-the-transformation-card.md) inverted the original direction). Where no direct verb exists, the model answer uses the closest paraphrase. Syntax rewrites (participial attribute, relative clause) are not in v1.
  - **Translation prompt:** dropped by [0049](../decisions/0049-drop-the-translation-card-and-the-hint-language.md). It doubled the cards per chunk without training anything the transformation card does not.
  - The back shows a one-line German meaning of the chunk. Fields and layout are in [Note types](../learning-design/note-types.md).
- **R16. Required hint language.** Dropped by [0049](../decisions/0049-drop-the-translation-card-and-the-hint-language.md): only the translation prompt used a hint language, so there is no such setting. ([0015](../decisions/0015-set-v1-run-defaults.md))
- **R17. LLM behind an interface.** Generated content (model answers, verbal rewrites, meanings) comes from an LLM provider interface. The Claude API is the first adapter, with `claude-opus-5-5` as the default model. A headless `claude -p` adapter for testing and a DeepSeek adapter can be added without touching callers. ([0004](../decisions/0004-generate-card-content-through-a-pluggable-llm-provider.md))
- **R18. No audio in v1.** Text-to-speech is out of scope; if added, it goes behind its own provider interface.

## Anki export

- **R19. Live push through AnkiConnect.** Notes go into the running Anki desktop app over AnkiConnect, not through `.apkg` files. ([0003](../decisions/0003-push-notes-live-through-ankiconnect.md))
- **R20. Tool-owned deck and note types.** The tool creates and owns its deck and note types and never modifies other decks. Note types are versioned, because changing their fields later means migrating existing notes.
- **R21. Fully automatic.** There is no review step: generated notes go straight into Anki. ([0005](../decisions/0005-push-cards-automatically-with-tagging-and-dry-run.md))
- **R22. Traceability tags.** Every note is tagged with the LLM provider, the model and a run ID, so that a bad batch can be found and deleted in Anki.
- **R23. Dry run.** `sync --dry-run` runs every `sync` stage, including generation, and prints what would be added without writing to Anki.
- **R23a. Partial failures.** During `sync`, a failing candidate stays pending with its error recorded and the run continues; the run ends with a summary and a non-zero exit code if anything failed. Errors that make every further step fail (Anki unreachable, missing API key) stop the run at once. ([0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md))

## Local state and configuration

- **R24. SQLite state.** A local SQLite database records processed sources, every extracted candidate (pushed or not), and cached LLM output, so that re-ranking or re-generating never refetches a source or pays twice for the same call. ([0007](../decisions/0007-keep-local-state-in-sqlite.md))
- **R25. State and config live outside the repo.** Secrets are read from environment variables or a git-ignored `.env`. Config and the database live in per-user directories (XDG: `~/.config/learn-german/`, `~/.local/share/learn-german/`), never in the working tree.

## Quality and CI

- **R26. Stack.** Python 3.12+ with `uv` for dependency management; MIT licence. Libraries and tools are fixed in [0016](../decisions/0016-use-standard-python-tooling.md). ([0002](../decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md), [0010](../decisions/0010-license-the-code-under-mit.md))
- **R27. CI on every push** (GitHub Actions): `ruff` lint and format check, a strict type check, `pytest`, and the docs validator. Extended by [0019](../decisions/0019-gate-main-with-ci-checks.md) with the lock check, import-linter, coverage, NLP tests and a PR-title check.
- **R28. CI needs no secrets and no Anki.** AnkiConnect and the LLM are mocked in tests. Test fixtures use synthetic or freely licensed German text, never copied news articles.

## Non-goals

- Multi-user support, accounts, hosting or sync across devices.
- A web UI or browser extension.
- A manual review or approval step before cards reach Anki.
- A per-run LLM spending limit (the cap in R12 bounds cost).
- Scheduled or unattended runs.
- Audio and chunk cloze cards in v1.
- Publishing or sharing generated decks.

## Deferred (design must leave room)

| Feature | Seam that must exist |
|---|---|
| YouTube subtitles, learner's own writing, `.epub`/`.pdf` | Ingest adapter interface (R5) |
| Formal prepositions, verb + preposition, collocations | Extractor interface (R9) |
| Known-item filtering | Filter stage (R14) |
| More ranking signals (external frequency list, curated NVV list) | Ranker interface (R13) |
| DeepSeek, `claude -p`, local models | LLM provider interface (R17) |
| Audio | Separate TTS provider interface (R18) |
| More examples per chunk | Candidates kept in SQLite (R24) |

## Open questions

- **Quality of automatic transformations:** with no review step and no self-check pass, how often LLM output is wrong. Measure this once v1 runs, and revisit [0005](../decisions/0005-push-cards-automatically-with-tagging-and-dry-run.md) if the error rate is high. The method, rubric and thresholds are in [Card quality of v1](../research/card-quality-v1.md); the results are still to be recorded there by the owner.

## Related

- [Learning goals](learning-goals.md)
- [DeepSeek chat advice](../research/deepseek-chat-advice.md)

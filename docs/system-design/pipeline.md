---
title: Pipeline
summary: Stages from source to Anki note, which command (add or sync) owns each, and what each stage reads from and writes to SQLite.
status: active
updated: 2026-11-26
---

# Pipeline

## Purpose

Shows the stages a source goes through on its way to Anki notes and which CLI command runs each one. The command split is decided in [0017](../decisions/0017-split-the-cli-into-add-and-sync.md). Read this before adding a stage, a command or a plug-in.

## Overview

```
add                                     sync
───────────────────────────────         ────────────────────────────────────────────────────────────
source ─► ingest ─► extract ─► SQLite ─► filter ─► rank ─► cap ─► pick ─► generate ─► push ─► SQLite
          (adapter) (extractors)         (dedupe,          (top   (one    (LLM,       (Anki-
                                          known)            N)     sent.)  cached)     Connect)

reextract: stored text ─► extract ─► SQLite
```

Everything left of SQLite is free and local apart from fetching. Everything right of it costs LLM calls or writes to Anki, and is bounded by the cap and previewed by `--dry-run`.

## `add`: ingest and extract

| Stage | Interface | Reads | Writes |
|---|---|---|---|
| Ingest | Source adapter (R5): news URL, local file | URL or path | Source row: reference, title, fetch time, content hash, text |
| Extract | Chunk extractor (R9): NVV in v1 | Source text | Candidate rows: chunk key, kind, sentence, context window, source. Status is tracked per chunk key, not per row ([0025](../decisions/0025-track-note-progress-per-chunk-key.md)) |

- A source already in the database is skipped unless `--force` is given (R6): a known URL before it is fetched, a known text after. `--force` fetches again and refreshes the stored source in place, updating its candidates by the `reextract` rules ([0042](../decisions/0042-recognise-known-sources-before-fetching-and-refresh-them-in-place.md)).
- A source that fails (blocked, paywalled, too little text) is reported and skipped; the others continue ([0013](../decisions/0013-fetch-articles-politely-without-bypassing-paywalls.md), [0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md)).
- Each source is extracted outside any transaction and stored in its own unit of work.
- Output per source: number of chunks found and how many have keys not yet seen in the database. Details, including fetching and exit codes, are in [Ingest](ingest.md).

## `sync`: select, generate, push

A `sync` is one run: it gets a run ID ([0016](../decisions/0016-use-standard-python-tooling.md)) and ends with a run summary.

| Stage | Interface | What it does |
|---|---|---|
| Read | `CandidateRepository.pending_chunks()` | Every chunk key not yet done in `pushed_notes`, with its occurrence count and missing note kinds ([Data model](../data/data-model.md#pending-chunks)). |
| Filter | Filter chain (R14) | `AlreadyInDeckFilter` narrows each chunk's missing note kinds to those Anki does not already have and drops chunks with none left (R11). "Already in the deck" means a note of the tool's note type anywhere in the collection, not only in the deck ([0033](../decisions/0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md), [0039](../decisions/0039-read-existing-keys-per-note-type-across-the-collection.md)). Known-item filters plug in here later. |
| Rank | Ranker (R13) | `OccurrenceRanker`: partial chunks first, then most occurrences across all processed sources, then the chunk key ([0034](../decisions/0034-rank-partial-chunks-first-then-by-occurrences.md)). |
| Cap | — | Keeps the top N chunks (`--cap`, then environment variable, then 10; R12). N counts chunks, not notes. |
| Pick | Occurrence picker | `ShortestSentencePicker` chooses the sentence and context that feed the cards: the shortest sentence of at least ten words, else the longest; the most recent on ties ([0032](../decisions/0032-feed-cards-from-the-shortest-sentence-of-ten-words.md)). |
| Generate | LLM provider (R17) | One call per chunk returns the shortened sentence, verbal-style rewrite, translation and meaning ([0012](../decisions/0012-make-both-cards-practise-the-chunk.md)). Responses are cached in SQLite. |
| Push | AnkiConnect (R19) | Adds the missing notes for each chunk, tagged with provider, model and run ID (R22). |

- Filtering and ranking happen at `sync` time, never at `add` time, because the deck and the occurrence counts change between commands.
- Read to pick is `ChunkSelector.select(cap)` in `application/selection/`. It reads in two short unit-of-work blocks, before and after the filters, so the database is not held while Anki is asked; call it outside any `with uow:` block. Its result pairs each chunk with its picked occurrence and builds the `CardRequest`.
- In `--dry-run` with Anki unreachable, the selector gets an empty filter chain, so deduplication rests on `pushed_notes` alone.
- `--dry-run` runs every stage up to push and prints the notes instead of pushing them (R23). Its LLM calls are cached, so a following real `sync` does not pay again.
- A failing chunk stays pending with its error recorded and the run continues; Anki being unreachable or a missing API key stops the run at once (R23a).

## `reextract`

Reruns the extractors over stored source text after the extractor or the light-verb list changes. Candidates found again keep their status, new ones are added as pending, pending ones no longer found are removed, and ones that already have notes are kept. "Has notes" means the chunk key has a row in `pushed_notes` ([0025](../decisions/0025-track-note-progress-per-chunk-key.md)). The rules live in `application/extraction.py` and are shared with `add --force`.

## `status`

Lists the five most recent sources, the number of pending and partial chunks, and the top pending chunks (`--top`, default 10) from `pending_chunks()`, ordered by the same `OccurrenceRanker` as `sync`, without asking Anki. A chunk Anki already has may show as pending there; `sync` skips it.

## Related

- [Ingest](ingest.md)
- [Requirements](../product/requirements.md)
- [Note types](../learning-design/note-types.md)

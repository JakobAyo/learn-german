---
title: Pipeline
summary: Stages from source to Anki note, which command (add or sync) owns each, and what each stage reads from and writes to SQLite.
status: active
updated: 2026-11-25
---

# Pipeline

## Purpose

Shows the stages a source goes through on its way to Anki notes and which CLI command runs each one. The command split is decided in [0017](../decisions/0017-split-the-cli-into-add-and-sync.md). Read this before adding a stage, a command or a plug-in.

## Overview

```
add                                     sync
───────────────────────────────         ─────────────────────────────────────────────────────
source ─► ingest ─► extract ─► SQLite ─► filter ─► rank ─► cap ─► generate ─► push ─► SQLite
          (adapter) (extractors)         (dedupe,          (N     (LLM,       (Anki-
                                          known)            chunks) cached)    Connect)

reextract: stored text ─► extract ─► SQLite
```

Everything left of SQLite is free and local apart from fetching. Everything right of it costs LLM calls or writes to Anki, and is bounded by the cap and previewed by `--dry-run`.

## `add`: ingest and extract

| Stage | Interface | Reads | Writes |
|---|---|---|---|
| Ingest | Source adapter (R5): news URL, local file | URL or path | Source row: reference, title, fetch time, content hash, text |
| Extract | Chunk extractor (R9): NVV in v1 | Source text | Candidate rows: chunk key, kind, sentence, context window, source. Status is tracked per chunk key, not per row ([0025](../decisions/0025-track-note-progress-per-chunk-key.md)) |

- A source already in the database (same URL or content hash) is skipped unless `--force` is given (R6).
- A source that fails (blocked, paywalled, too little text) is reported and skipped; the others continue ([0013](../decisions/0013-fetch-articles-politely-without-bypassing-paywalls.md), [0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md)).
- Output per source: number of chunks found and how many have keys not yet seen in the database.

## `sync`: select, generate, push

A `sync` is one run: it gets a run ID ([0016](../decisions/0016-use-standard-python-tooling.md)) and ends with a run summary.

| Stage | Interface | What it does |
|---|---|---|
| Filter | Filter chain (R14) | Drops chunks that already have both notes in the Anki deck, checked per note type (R11). Known-item filters plug in here later. |
| Rank | Ranker (R13) | Orders the remaining chunk keys by occurrences across all processed sources, most frequent first. |
| Cap | — | Keeps the top N chunks (`--cap`, then environment variable, then 10; R12). |
| Generate | LLM provider (R17) | One call per chunk returns the shortened sentence, verbal-style rewrite, translation and meaning ([0012](../decisions/0012-make-both-cards-practise-the-chunk.md)). Responses are cached in SQLite. |
| Push | AnkiConnect (R19) | Adds the missing notes for each chunk, tagged with provider, model and run ID (R22). |

- Filtering and ranking happen at `sync` time, never at `add` time, because the deck and the occurrence counts change between commands.
- `--dry-run` runs every stage up to push and prints the notes instead of pushing them (R23). Its LLM calls are cached, so a following real `sync` does not pay again.
- A failing chunk stays pending with its error recorded and the run continues; Anki being unreachable or a missing API key stops the run at once (R23a).

## `reextract`

Reruns the extractors over stored source text after the extractor or the light-verb list changes. Candidates found again keep their status, new ones are added as pending, pending ones no longer found are removed, and ones that already have notes are kept.

## Open questions

- **Which occurrence feeds the cards.** A chunk key often has several candidate sentences across sources. `sync` must pick one to send to the LLM (for example the shortest, or the most recent). Decide when implementing generation.

## Related

- [Requirements](../product/requirements.md)
- [Note types](../learning-design/note-types.md)

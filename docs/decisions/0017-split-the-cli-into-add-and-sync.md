---
title: Split the CLI into add and sync, with extraction at add time
summary: add fetches and extracts sources into SQLite; sync ranks, deduplicates, generates and pushes up to the cap; reextract rebuilds candidates from stored text.
status: active
updated: 2026-11-24
---

# Split the CLI into add and sync, with extraction at add time

## Context

The requirements describe one "run" going from source to Anki, but no decision fixed the command layout. The owner wants to collect many sources first and turn them into cards later, all at once or a capped number at a time. Pending candidates are already kept in SQLite ([0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)), and source text is stored so it never has to be fetched again ([0007](0007-keep-local-state-in-sqlite.md)). The open question was where to split the pipeline: after fetching or after extraction.

## Decision

The CLI has two main commands and two helpers:

| Command | Does | Cost |
|---|---|---|
| `learn-german add <url\|file>... [--from FILE] [--force]` | Fetch or read each source, store its text, run the extractors and store the candidates. Prints the chunks found per source and how many are new. `--from` reads one URL or path per line. | Network and local CPU only |
| `learn-german sync [--cap N] [--dry-run]` | Load pending candidates, filter (including deduplication against Anki), rank, take the top N chunks, generate with the LLM and push to Anki. | LLM calls and Anki writes |
| `learn-german status` | Show processed sources, pending chunk count and the top-ranked pending chunks. | None |
| `learn-german reextract` | Rerun the extractors over the stored source text, without fetching. | Local CPU only |

- **The split is after extraction.** `add` fetches and extracts. `sync` does everything that costs money or changes Anki.
- **A run is a `sync`.** The run ID, the cap, `--dry-run` and the run summary all belong to `sync`. `add` reports its own per-source summary.
- **Selection happens at `sync` time.** Deduplication against Anki and ranking are done when `sync` runs, not when a source is added, because the deck and the occurrence counts change between commands.
- **`add` never stops at one bad source.** A source that is blocked, paywalled or empty is reported and skipped, the rest are processed, and the command exits non-zero if any failed. This applies [0014](0014-keep-progress-when-a-run-fails-partway.md) to ingest.
- **`reextract` keeps candidate history.** Candidates it finds again keep their status, new ones are added as pending, and pending ones it no longer finds are removed. Candidates that already have notes are kept.

## Alternatives considered

- One command that fetches, extracts, generates and pushes: rejected. Adding sources means generating cards straight away, and ranking only sees what has been added so far.
- Split after fetching (`fetch`, then `extract` and generate together): rejected. Ranking counts chunk occurrences across all sources ([0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)), so every source must be extracted before the cap can choose. The cap counts chunks, not sources, so "process only some fetched sources" does not fit it. Extraction is cheap and local, so there is no reason to postpone it. `reextract` gives the benefit of a separate fetch step, which is changing the extractor without fetching again.
- Three steps, `fetch`, `extract` and `sync`, all required: rejected. It adds a command to every normal use for no gain over `reextract`.

## Consequences

- Adding many sources before a `sync` makes frequency ranking useful. With one source per run, most chunks occur once and ranking does little.
- `add` gives immediate feedback on whether a source was worth adding.
- A change to the light-verb list or a new extractor is applied to old sources with `reextract`.
- Requirements R6, R12, R23 and R23a now refer to `add` and `sync` instead of a single run. The stages and which command owns each are in [Pipeline](../system-design/pipeline.md).

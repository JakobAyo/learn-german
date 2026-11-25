---
title: Track note progress per chunk key, not per occurrence
summary: Candidates are occurrences without status; pushed notes and errors are stored per chunk key, and pending, partial or done is derived from them.
status: active
updated: 2026-11-25
---

# Track note progress per chunk key, not per occurrence

## Context

[0014](0014-keep-progress-when-a-run-fails-partway.md) requires a status that tells apart a chunk with no notes, one of its two notes, and both. [0007](0007-keep-local-state-in-sqlite.md) and the [Roadmap](../product/roadmap.md) speak of a *candidate* status. But a candidate is one occurrence of a chunk in one sentence, and the same chunk key usually has several occurrences across sources. Notes, on the other hand, are created once per key and note kind ([0012](0012-make-both-cards-practise-the-chunk.md)). A status on every occurrence row would have to be kept in step across all rows of a key, and would drift as soon as `add` or `reextract` inserts a new occurrence of a key that already has notes.

## Decision

- A `Candidate` is an occurrence only: key, kind, sentence, context, and the source it belongs to. It has no status.
- Progress lives per chunk key in two tables: `pushed_notes` (one row per key and note kind, with the run ID) and `chunk_errors` (the last failure per key).
- `ChunkState` in the domain combines them. Its `status` (`pending`, `partial`, `done`) and its `missing` note kinds are derived, never stored, so they cannot disagree with the pushed notes.
- An error does not change the status, so a failed chunk stays `pending` or `partial` and the next sync retries it, as 0014 requires.

The tables are described in [Data model](../data/data-model.md).

## Alternatives considered

- Status column on each candidate row: matches the original wording, but needs every row of a key updated together, and new occurrences of a finished chunk would arrive as `pending`.
- A `chunks` table with one row per key and a stored status column: one more table to keep consistent with `candidates`, and a stored status can disagree with which notes were actually pushed.

## Consequences

- "Pending chunks" for `status` and `sync` are the distinct keys in `candidates` whose state is not `done`; occurrence counts for ranking come from the same table.
- `reextract` (0017) can decide "has notes" by looking up the key in `pushed_notes` instead of a candidate's status.
- Anki stays the source of truth for deduplication (R11). `pushed_notes` is the local record and a fast path; if the two disagree, the Anki check in M4 wins.

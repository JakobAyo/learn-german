---
title: Data model
summary: SQLite tables and constraints, how chunk status and pending chunks are derived from candidates and pushed notes, and how migrations are applied.
status: active
updated: 2026-11-26
---

# Data model

## Purpose

Describes the local SQLite database ([0007](../decisions/0007-keep-local-state-in-sqlite.md)): what each table holds, which constraints enforce the rules from the requirements, and how the schema changes over time. Read this before writing a query, a repository method or a migration. The domain types the tables map to are in `src/learn_german/domain/models.py`.

## Location

`~/.local/share/learn-german/learn-german.db` by default (the XDG data directory), or the `database_path` setting ([Configuration](../development/configuration.md)). It holds copyrighted source text, so it never goes into the repository.

## Tables

All tables are `STRICT`. Times are ISO 8601 strings in UTC, written by the repositories; the domain only accepts timezone-aware times.

### `sources`

One row per processed source (R5, R6).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Primary key, the domain's `SourceId` |
| `ref` | TEXT | URL or file path, **unique** |
| `kind` | TEXT | `SourceKind`: `news-url` or `local-file` |
| `title` | TEXT | Nullable |
| `fetched_at` | TEXT | When the text was fetched or read |
| `content_hash` | TEXT | SHA-256 of the normalised text, **unique** |
| `text` | TEXT | The full text, so `reextract` never fetches again (0017) |

Unique `ref` and unique `content_hash` together implement R6: a source is known by its address or by its text. Adding a duplicate raises `DuplicateSourceError`.

### `candidates`

One row per occurrence of a chunk in a source sentence (R10). Many rows can share a chunk key.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Primary key; also gives insertion order |
| `source_id` | INTEGER | References `sources.id`, deleted with its source |
| `chunk_key` | TEXT | 0011 format, indexed |
| `kind` | TEXT | `ChunkKind`: `nvv` |
| `sentence` | TEXT | The source sentence |
| `context` | TEXT | The sentence with one sentence either side |

`(source_id, chunk_key, sentence)` is unique. Adding the same occurrence again updates its kind and context instead of duplicating it. Occurrence counts for ranking (R13) are `COUNT(*)` grouped by `chunk_key`, so the same sentence in two sources counts twice.

### `pushed_notes`

One row per note the tool has pushed to Anki (0012, 0014).

| Column | Type | Notes |
|---|---|---|
| `chunk_key` | TEXT | Part of the primary key |
| `note_kind` | TEXT | `NoteKind`: `transformation` or `translation`; part of the primary key |
| `run_id` | TEXT | The sync that pushed it, `run-YYYYMMDD-HHMM` |
| `pushed_at` | TEXT | |

### `chunk_errors`

The last failure per chunk during a sync (0014). One row per chunk key at most; a new failure replaces it, a success clears it.

| Column | Type | Notes |
|---|---|---|
| `chunk_key` | TEXT | Primary key |
| `message` | TEXT | The error message shown in the run summary |
| `failed_at` | TEXT | |

### `llm_cache`

Raw LLM responses (0004), so an identical request is never paid for twice.

| Column | Type | Notes |
|---|---|---|
| `cache_key` | TEXT | Primary key; hash of provider, model, prompt version and request, computed by the caching decorator (M5) |
| `provider`, `model`, `prompt_version` | TEXT | Kept for inspection and clean-up, not for lookup |
| `response` | TEXT | Raw response; validated again when read |
| `created_at` | TEXT | |

## Chunk status

Progress is tracked per chunk key, not per occurrence, because notes belong to a key ([0025](../decisions/0025-track-note-progress-per-chunk-key.md)). The status is derived, never stored:

| Rows in `pushed_notes` for the key | `ChunkStatus` | Missing note kinds |
|---|---|---|
| none | `pending` | both |
| one | `partial` | the other one |
| both | `done` | none |

A chunk with a row in `chunk_errors` keeps its status, so a failed chunk stays `pending` (or `partial`) and the next sync retries it. Anki stays the source of truth for deduplication (R11); `pushed_notes` is the local record and a fast path.

## Pending chunks

`CandidateRepository.pending_chunks()` is the one query selection and `status` start from. It returns one `PendingChunk` per distinct `chunk_key` in `candidates` whose status is not `done`, ordered by key:

| Field | Comes from |
|---|---|
| `key` | `candidates.chunk_key` |
| `kind` | `kind` of the key's oldest candidate row (lowest `id`) |
| `occurrences` | `COUNT(*)` of the key's rows in `candidates`, over all sources |
| `missing` | the note kinds with no row in `pushed_notes` for the key |

A row in `pushed_notes` for a key without any candidate row is ignored. During `sync`, the Anki check can only narrow `missing` further: a note kind counts as present if `pushed_notes` or the Anki deck has it ([0033](../decisions/0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)). So a locally done chunk is never sent to Anki, and a note the learner deleted in Anki is not re-created.

## Migrations

- Numbered files in `src/learn_german/adapters/storage/sqlite/migrations/`, named `NNNN_short_name.sql`, numbered from `0001` without gaps. They ship as package data.
- `PRAGMA user_version` holds the number of the last migration applied. Opening the database applies every newer file in order, each in its own transaction together with the version bump, so a failed migration leaves the previous version intact.
- A database with a higher version than the code knows is refused with a message to upgrade.
- Never edit a migration that has been released. Add the next number instead.

## Related

- [Pipeline](../system-design/pipeline.md)
- [Code architecture](../system-design/code-architecture.md)
- [0007 Keep local state in SQLite](../decisions/0007-keep-local-state-in-sqlite.md)

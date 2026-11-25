-- Initial schema. Times are ISO 8601 strings in UTC. See docs/data/data-model.md.

CREATE TABLE sources (
    id           INTEGER PRIMARY KEY,
    ref          TEXT NOT NULL UNIQUE,
    kind         TEXT NOT NULL,
    title        TEXT,
    fetched_at   TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    text         TEXT NOT NULL
) STRICT;

CREATE TABLE candidates (
    id        INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    chunk_key TEXT NOT NULL,
    kind      TEXT NOT NULL,
    sentence  TEXT NOT NULL,
    context   TEXT NOT NULL,
    UNIQUE (source_id, chunk_key, sentence)
) STRICT;

CREATE INDEX candidates_by_chunk_key ON candidates (chunk_key);

CREATE TABLE pushed_notes (
    chunk_key TEXT NOT NULL,
    note_kind TEXT NOT NULL,
    run_id    TEXT NOT NULL,
    pushed_at TEXT NOT NULL,
    PRIMARY KEY (chunk_key, note_kind)
) STRICT;

CREATE TABLE chunk_errors (
    chunk_key TEXT PRIMARY KEY,
    message   TEXT NOT NULL,
    failed_at TEXT NOT NULL
) STRICT;

CREATE TABLE llm_cache (
    cache_key      TEXT PRIMARY KEY,
    provider       TEXT NOT NULL,
    model          TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    response       TEXT NOT NULL,
    created_at     TEXT NOT NULL
) STRICT;

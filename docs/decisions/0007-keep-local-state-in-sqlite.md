---
title: Keep local state in SQLite
summary: A local SQLite database stores processed sources, all extracted candidates and cached LLM output, outside the repository.
status: active
updated: 2026-11-24
---

# Keep local state in SQLite

## Context

Runs must not refetch sources they already processed or pay twice for the same LLM call. Candidates beyond the per-run cap should stay available for later runs, and deferred features (known-item filtering, several examples per chunk, re-ranking) need the history.

## Decision

- One SQLite database, stored in the XDG data directory (`~/.local/share/learn-german/`), never in the repo.
- It records processed sources (URL or content hash, fetch time, text), extracted candidates (chunk key, kind, sentence, context, source reference, status such as pending, pushed or skipped), and LLM responses keyed for caching.
- The schema is versioned and migrated in code.

## Alternatives considered

- Stateless, with Anki as the only store: rejected. Every run would refetch and re-extract, and unpushed candidates would be lost.
- JSON files: rejected. They do not support querying or deduplication across thousands of candidates.

## Consequences

- Anki holds what was pushed; SQLite holds everything else. Deduplication checks Anki, the source of truth for what the learner studies, and may use SQLite as a fast path.
- The database contains copyrighted source text, so it must never be committed.

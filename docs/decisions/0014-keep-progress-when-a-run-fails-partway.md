---
title: Keep progress when a run fails partway
summary: A failing candidate stays pending with its error recorded, the run continues, and a summary lists failures; the next run retries them.
status: active
updated: 2026-11-24
---

# Keep progress when a run fails partway

## Context

A run calls the network, the LLM and AnkiConnect for each chunk. Any of them can fail partway through: a rate limit, a malformed response, Anki being closed.

## Decision

- Notes already pushed stay in Anki.
- A candidate whose generation or push fails stays `pending` in SQLite, with the error and time recorded, and the run moves on to the next candidate.
- The run ends with a summary of what was added, skipped and failed. It exits with a non-zero code if anything failed.
- The next run picks failed candidates up again, since they are still pending. LLM output that succeeded is cached, so a retry does not pay twice (see [0004](0004-generate-card-content-through-a-pluggable-llm-provider.md)).
- An error that makes every further step fail, such as AnkiConnect being unreachable or the API key missing, stops the run at once instead of failing each candidate.
- A chunk's two notes are pushed together. If the second push fails, the next run creates only the missing note, because deduplication checks each note type separately (see [0012](0012-make-both-cards-practise-the-chunk.md)).

## Alternatives considered

- Stop at the first error: rejected, because one bad LLM response would block the rest of the run.
- All or nothing: rejected, because it throws away a whole run's paid work over one failure.

## Consequences

- Candidate status must distinguish a chunk with no notes, a chunk with one of its two notes, and a chunk with both.
- Failures that repeat forever need a retry limit; this can be added once it happens in practice.

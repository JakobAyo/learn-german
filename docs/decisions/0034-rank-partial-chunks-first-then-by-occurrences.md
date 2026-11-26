---
title: Rank partial chunks first, then by occurrences, ties by key
summary: OccurrenceRanker puts chunks that already have one note first, then orders by occurrence count, most first, and breaks ties by the chunk key.
status: active
updated: 2026-11-26
---

# Rank partial chunks first, then by occurrences, ties by key

## Context

R13 and [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md) rank chunks by how often they occur in the learner's sources; the [Roadmap](../product/roadmap.md) asks for ties to be broken deterministically. Most chunks occur once when few sources are stored, so ties are the normal case, not the exception. A chunk whose second note failed to push ([0014](0014-keep-progress-when-a-run-fails-partway.md)) is partial: one card is in Anki, the other is not. Ranked by occurrences alone, it can sit behind newer, more frequent chunks for many runs while the learner drills only half of it.

## Decision

`OccurrenceRanker` (`application/selection/ranking.py`) sorts by three keys in turn:

1. **Partial chunks first**: a chunk that already has one of its note kinds, locally or in Anki ([0033](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)).
2. **Occurrences**, most first, counted in SQL over all candidate rows of the key.
3. **Chunk key**, in code-point order, so the result never depends on the input order.

The ranker is a pure function of the chunks. `sync` and `status` share it, so `status` shows pending chunks in the order `sync` would take them.

## Alternatives considered

- **Occurrences only, ties by key:** what the roadmap described, but leaves partial chunks waiting behind new ones.
- **Ties by first or last time seen:** favours old or fresh material, but the `Ranker` port receives `PendingChunk`s, which carry no time, and adding one changes a frozen domain type.
- **Retry chunks with a recorded error first:** a chunk that fails every time would take a cap slot on every run; 0014 leaves a retry limit for later.

## Consequences

- Finishing a partial chunk uses a cap slot but usually no new LLM call, since its output is cached.
- Key order is alphabetical and carries no meaning; it only makes runs and tests repeatable.
- More ranking signals (R13) change this ranker or add another `Ranker`; partial-first should stay on top of any of them.

## Related

- [Pipeline](../system-design/pipeline.md)
- [0009 Deduplicate by chunk key, rank and cap](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)

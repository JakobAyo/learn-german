---
title: Count a note as present if the local record or Anki has it
summary: A note kind is needed only if neither pushed_notes nor the Anki deck has it, so locally done chunks skip Anki and a note deleted in Anki stays deleted.
status: active
updated: 2026-11-26
---

# Count a note as present if the local record or Anki has it

## Context

Two places know which notes exist: the local `pushed_notes` table ([0025](0025-track-note-progress-per-chunk-key.md)) and the Anki deck, which R11 makes the source of truth for deduplication. 0025 calls `pushed_notes` a fast path and says the Anki check wins if the two disagree, but not what selection does in each direction of disagreement:

- Anki has a note the local record does not know about (the database was deleted, or notes were imported by hand).
- The local record has a note Anki no longer has (the learner deleted it, for example a bad batch found by its run tag as [0005](0005-push-cards-automatically-with-tagging-and-dry-run.md) suggests).

## Decision

- A note kind counts as **present** for a chunk if `pushed_notes` **or** the Anki deck has it. Selection creates only note kinds that neither has.
- `CandidateRepository.pending_chunks()` leaves out chunks that are done locally and sets `missing` from `pushed_notes`. So the fast path is real: a locally done chunk never reaches the Anki check.
- `AlreadyInDeckFilter` can only **narrow** `missing`, never widen it, as the `CandidateFilter` port says. It drops chunks whose missing kinds are all in the deck.
- This refines 0025: "the Anki check wins" holds when Anki has a note the local record lacks, which is the duplicate case R11 is about. A note deleted in Anki is not re-created.

## Alternatives considered

- **Anki alone decides:** every chunk, done or not, would be checked against Anki on each sync, `status` could not tell what is pending without Anki, and a learner who deletes a bad note would get it back on the next sync, from the same cached LLM output.
- **Local record alone decides:** a lost or reset database would push duplicates of every note already in Anki, which R11 forbids.

## Consequences

- Deleting a note in Anki is final for that chunk and note kind. Getting it back needs its `pushed_notes` row removed; there is no command for that in v1.
- `status`, which does not talk to Anki, can list pending chunks from the database alone. It may show a chunk as pending that Anki already has; `sync` then skips it.
- `sync --dry-run` with Anki unreachable uses an empty filter chain and still skips locally done chunks.

## Related

- [Data model](../data/data-model.md)
- [Pipeline](../system-design/pipeline.md)
- [0025 Track note progress per chunk key](0025-track-note-progress-per-chunk-key.md)

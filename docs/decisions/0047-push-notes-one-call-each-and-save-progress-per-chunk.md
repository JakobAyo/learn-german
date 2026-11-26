---
title: Push a chunk's notes one call each and save progress per chunk
summary: sync adds each missing note in its own add_notes call and saves pushed notes and errors per chunk; a fatal error keeps what was pushed, prints the summary so far and exits 2.
status: active
updated: 2026-11-26
---

# Push a chunk's notes one call each and save progress per chunk

## Context

[0014](0014-keep-progress-when-a-run-fails-partway.md) says a failing chunk stays pending with its error, the run goes on, and an error that makes every further step fail stops the run at once. Progress is stored per chunk key ([0025](0025-track-note-progress-per-chunk-key.md)). `AnkiGateway.add_notes` stops at the first rejected note and keeps the ones before it, but says only that one failed ([0040](0040-add-notes-one-call-each-and-split-ankiconnect-errors.md)). `CachingProvider` opens its own transactions, so generation cannot run inside a chunk's `with uow:` block ([0036](0036-check-card-content-then-cache-it-in-its-own-transaction.md)), and [0045](0045-build-the-cli-with-create-app-and-stream-outcomes.md) wants use cases to yield an outcome per item after it is saved.

## Decision

- **Two steps.** `SyncService.start(cap, dry_run)` takes the run ID from the injected clock, runs the preflight ([0046](0046-check-settings-and-anki-before-selecting-and-keep-dry-runs-read-only.md)) and selects. It returns a `SyncRun` whose `chunks()` processes the selected chunks in rank order and yields a `ChunkOutcome` per chunk once its state is saved, and whose `summary()` is the `RunSummary` of the chunks done so far.
- **Per chunk:** generate outside any unit of work, build the notes of the chunk's missing kinds in `NoteKind` order (transformation, then translation), and add them with **one `add_notes` call per note**, so the notes added before a rejection are known. Then one unit of work records a `pushed_notes` row per added note with the run ID, and records the chunk's error or clears an earlier one.
- **`ItemError`** (unusable output, a call that failed after retries, a rejected note): the error is recorded, the notes added before it stay recorded, and the run goes on. The next sync adds only the missing note, from the cached content.
- **`FatalError`** (Anki gone, key rejected, database failure): the notes already added for the chunk are still recorded, its error is left as it was, and the error propagates. The CLI prints the summary of the run so far, marked as stopped early, then `Error: …` on stderr, and exits 2.
- **Output** goes through `cli/presenters.py`: a header with the run ID and the tags every note carries (R22), one line per chunk as it finishes (`added`, `would add` or `failed`, with any note added before a failure), in a dry run each note's fields, and a summary that lists every failed chunk. With nothing to do, `sync` says so and points to `add`.
- **Exit codes** as in 0045: 0 when every chunk worked or none was pending, 1 when at least one chunk failed, 2 for a fatal or usage error.
- `sync` takes `--cap N` (a flag above the `cap` setting, R12) and `--dry-run`. No other flags in v1.

## Alternatives considered

- **One `add_notes` call per chunk:** fewer calls, but after a rejection the tool cannot tell whether the first note went in, so `pushed_notes` would be incomplete until the next sync's Anki check.
- **Record each note in its own unit of work as soon as it is added:** a little safer against a crash between two notes, but the Anki check of [0033](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md) already covers that window, and one block per chunk keeps the chunk's state consistent.
- **Also record notes that `AlreadyInDeckFilter` finds in Anki:** would make `status` agree with Anki sooner, but `ChunkSelector` drops those chunks before `sync` sees them, and recording them would turn a filter into a writer.
- **Print only a final report:** rejected in 0045; a long run would show nothing until the end.

## Consequences

- A chunk Anki already has stays pending locally and is skipped by every sync's Anki check; `status` may list it, as 0033 accepts.
- A fatal error halfway leaves the finished chunks' lines and summary on screen and their state in the database.
- Two syncs started in the same minute share a run ID and so a `run::` tag ([0016](0016-use-standard-python-tooling.md)).

## Related

- [Pipeline](../system-design/pipeline.md)
- [Code architecture](../system-design/code-architecture.md#error-model)

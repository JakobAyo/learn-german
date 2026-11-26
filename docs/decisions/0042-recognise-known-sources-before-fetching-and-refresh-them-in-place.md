---
title: Recognise known sources before fetching, and refresh them in place with --force
summary: add looks a reference up before fetching and the text after; --force fetches again, overwrites the stored row and updates its candidates by the reextract rules.
status: active
updated: 2026-11-26
---

# Recognise known sources before fetching, and refresh them in place with --force

## Context

R6 says `add` recognises a processed source by URL or content hash and skips it unless `--force` is given. It does not say when the check happens, nor what `--force` does to a source that is already stored. The `sources` table keeps `ref` and `content_hash` unique ([Data model](../data/data-model.md)), so a forced source cannot simply be inserted a second time. Notes are tracked per chunk key, not per candidate ([0025](0025-track-note-progress-per-chunk-key.md)), and [0017](0017-split-the-cli-into-add-and-sync.md) already defines how candidates change when a source is extracted again.

## Decision

- **Check the reference before fetching.** A URL that is already stored is skipped without any request, so `add` never fetches a known page twice (0013). The check uses the reference as typed.
- **Check the text after fetching.** The same text under another reference (a second URL of the same article, or a saved `.txt` copy) is skipped by its content hash. A local file is always caught here, because its stored reference is the absolute path.
- **A skip is not a failure.** It is reported per source and does not change the exit code.
- **`--force` refreshes in place.** The source is fetched again and the stored row it matches (by reference first, else by text) is overwritten: new text, hash, title and fetch time, same ID. Its candidates are then updated by the four 0017 rules, exactly as `reextract` does: found again kept, new added, vanished removed unless the chunk has notes. If the new text equals another stored source's text, the source fails with a clear message and nothing changes.
- **Ports.** `SourceRepository.find_id` takes either the reference or the hash alone, `SourceRepository.replace` overwrites a row, and `CandidateRepository.remove` deletes a source's occurrences by key and sentence. The 0017 rules live once, in `application/extraction.py`, and serve both `add --force` and `reextract`.

## Alternatives considered

- **Fetch first, then check by reference or hash:** simpler, but fetches every known URL again on each `add`, which 0013 rules out in spirit.
- **`--force` deletes the old row and inserts a new one:** the cascade would drop candidates of chunks that already have notes, so a partial chunk could lose its last occurrence and never get its second note.
- **`--force` adds a second row:** impossible under the unique constraints, and occurrence counts would double.

## Consequences

- The same URL typed differently (with a fragment, percent-encoded) is fetched once more, then skipped by its hash.
- `add --force` and `reextract` cannot drift apart, since they share the code that applies 0017.
- A forced refresh keeps the source's ID and the age of its kept candidates, so the occurrence picker's tie-break by age ([0032](0032-feed-cards-from-the-shortest-sentence-of-ten-words.md)) is stable.

## Related

- [Ingest](../system-design/ingest.md)
- [0017 Split the CLI into add and sync](0017-split-the-cli-into-add-and-sync.md)
- [0025 Track note progress per chunk key](0025-track-note-progress-per-chunk-key.md)

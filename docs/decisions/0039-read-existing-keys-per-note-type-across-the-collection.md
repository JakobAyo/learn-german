---
title: Read existing keys per note type across the whole collection
summary: existing_keys counts every note of the tool's note type wherever it is, not only in the deck, so it agrees with Anki's own duplicate check on add.
status: active
updated: 2026-11-26
---

# Read existing keys per note type across the whole collection

## Context

[0033](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md) counts a note as present if the local record or "the Anki deck" has it, and the `AnkiGateway.existing_keys` docstring says "in the deck". Anki itself checks duplicates on a note type's first field, and `addNote` does so across the whole collection unless told to look only in one deck. A learner may move notes out of the tool's deck, for example into a deck for leeches.

If the search looked only in the deck, a moved note would count as missing. `sync` would then pay for its content again and Anki would reject it as a duplicate on every run; with the duplicate check narrowed to the deck as well, the note would be pushed a second time.

## Decision

- `existing_keys(note_kind)` searches `"note:<note type name>"` with no deck term, so every note of the tool's note type counts, in any deck. Search syntax in the name (`\`, `"`, `*`, `_`) is escaped.
- Keys are read from the `ChunkKey` field through `notesInfo`. A value that is not a valid chunk key (edited by hand, or empty) is logged and skipped.
- `addNote` is sent with `allowDuplicate: false` and `duplicateScope: "collection"`, so the read and the write use the same notion of "already there".
- Only the current version of each note type is searched. When a `-v2` type arrives, its migration moves the old notes into it (0003).

## Alternatives considered

- **Only the deck (`deck:` with its subdecks):** matches 0033's wording, but disagrees with Anki's duplicate check as described above.
- **One `findNotes` per chunk with a `ChunkKey:` term:** fewer notes read, but one request per chunk and kind instead of two per run.

## Consequences

- This refines 0033: "the Anki deck" means the tool's note types anywhere in the collection. The docstring of `AnkiGateway.existing_keys` in `ports.py` should say so too.
- Moving notes to another deck does not bring them back; deleting them is still final, as 0033 says.
- `notesInfo` returns every note of a type in one answer. That is fine for thousands of notes; if it gets slow, the gateway can page the IDs without changing the port.

## Related

- [AnkiConnect](../integrations/ankiconnect.md)
- [0033 Count a note as present](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)

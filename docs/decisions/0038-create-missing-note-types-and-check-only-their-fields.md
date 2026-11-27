---
title: Create missing note types and check only their fields
summary: ensure_setup creates the deck and missing note types from package template files, fails if an existing type's fields differ, and never edits an existing type.
status: active
updated: 2026-11-26
---

# Create missing note types and check only their fields

## Context

[0003](0003-push-notes-live-through-ankiconnect.md) and R20 make the deck and the versioned note types the tool's own. The [Roadmap](../product/roadmap.md) asks `ensure_setup()` to create what is missing, to fail clearly when an existing note type's fields differ, and to be idempotent. It does not say what happens to an existing note type whose fields match but whose templates or styling differ, for example because the owner restyled the cards in Anki or because a later release changes a template.

## Decision

- `ensure_setup` first checks that AnkiConnect speaks API version 6 or later, then creates the deck if it is missing, then handles each note type of `NOTE_TYPES`:
  - **Missing:** created with `createModel` from its `NoteTypeSpec`: fields in order with `ChunkKey` first, one card template, and the shared CSS.
  - **Present with the same field names in the same order:** left untouched, including its templates and styling.
  - **Present with other fields:** `NoteTypeMismatchError` (fatal) before any note is added. The message names both field lists and says to restore the fields instead of editing them, because a field change is a migration (0003).
- Templates and CSS are package files in `adapters/anki/templates/`, loaded with `importlib.resources`. The back of each card starts with `{{FrontSide}}` and `<hr id="answer">`, Anki's usual layout, so the learner compares the model answer with the prompt. German fields carry `lang="de"`, the translation prompt `lang="{{HintLanguage}}"`.
- The field names exist twice: in `NoteBuilder` (application) and in the note type specs (adapter), because application code may not import an adapter ([0018](0018-structure-code-as-ports-and-adapters.md)). A test checks that they agree, and a frozen test asserts the v1 field lists literally.

## Alternatives considered

- **Overwrite templates and styling on every setup:** a template fix would reach existing notes at once, but every run would undo the owner's own restyling, and it costs two more calls per note type.
- **Fail when templates or styling differ:** too strict. A restyled card is harmless; only fields decide whether notes still fit.
- **Add missing fields automatically:** that is a migration, which 0003 wants done on purpose with a new `-vN` type, and it would not cover renamed or reordered fields.
- **Templates as Python strings:** harder to read and to diff than HTML files, and the conventions ask for data files through `importlib.resources`.

## Consequences

- The owner can restyle the cards in Anki; the tool never changes them back.
- A template change in a later release does not reach an existing note type by itself. It needs a new note type version or an explicit update step, decided in its own record.
- A field renamed by hand in Anki stops every `sync` until it is restored.

## Related

- [Note types](../learning-design/note-types.md)
- [AnkiConnect](../integrations/ankiconnect.md)

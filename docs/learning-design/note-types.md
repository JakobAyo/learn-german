---
title: Note types
summary: Deck, the v1 transformation note type and its fields, card front and back, and tags; fields are hard to change once notes exist.
status: active
updated: 2026-11-27
---

# Note types

## Purpose

Defines what v1 puts into Anki: the deck, the note type, its fields and what the card shows. Changing a field after notes exist needs a migration (see [0003](../decisions/0003-push-notes-live-through-ankiconnect.md)), so read this before touching the export or the generation prompt. The content rules come from [0012](../decisions/0012-make-both-cards-practise-the-chunk.md). Each chunk gets one note, of the transformation type; the translation-prompt type `learn-german-translation-v1` was dropped by [0049](../decisions/0049-drop-the-translation-card-and-the-hint-language.md), and the tool no longer creates, reads or counts its notes.

## Deck

`learn-german::chunks` by default, configurable. The tool only adds notes to this deck and never touches other decks. `ensure_setup` creates it if it is missing.

A note of the tool's note type counts as present wherever it is, so a note moved to another deck is not pushed again ([0039](../decisions/0039-read-existing-keys-per-note-type-across-the-collection.md)).

## Base fields

The note type starts with these fields, in this order, followed by the fields of its card below. They are kept separate so that a later card type can share them. `ChunkKey` is first because Anki checks duplicates on the first field within a note type.

| Field | Example | Source |
|---|---|---|
| `ChunkKey` | `entscheidung\|treffen` | extractor ([0011](../decisions/0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)) |
| `Chunk` | eine Entscheidung treffen | LLM, citation form ([0028](../decisions/0028-let-the-llm-supply-the-citation-form.md)) |
| `Meaning` | eine Entscheidung treffen = entscheiden, sich festlegen | LLM, one line in German |
| `Answer` | Die Regierung hat die Entscheidung getroffen, die Steuer zu senken. | LLM, shortened source sentence |

`ChunkKey` is not shown on any card. Field values are plain text: the gateway HTML-escapes them, so `<` or `&` in a sentence shows as written ([0040](../decisions/0040-add-notes-one-call-each-and-split-ankiconnect-errors.md)).

## Cards

The note type has one card type, named `Transformation`. The templates and the shared stylesheet are files in `src/learn_german/adapters/anki/templates/`; their rendering is pinned by golden files in `tests/data/anki/`.

- The back starts with the front, then a line (`{{FrontSide}}` and `<hr id="answer">`), so the model answer stands under the prompt.
- All text is German and carries `lang="de"`.
- The chunk is bold, the meaning italic and smaller. Night mode has its own colours.

`ensure_setup` creates a missing note type but never edits an existing one, so the cards can be restyled in Anki ([0038](../decisions/0038-create-missing-note-types-and-check-only-their-fields.md)).

## Transformation note type: `learn-german-transformation-v1`

Extra field:

| Field | Example |
|---|---|
| `Prompt` | Die Regierung hat entschieden, die Steuer zu senken. |

- **Front:** "Rewrite in verbal style, without the NVV:" followed by `Answer`, the sentence with the NVV.
- **Back:** the front, then `Prompt`, the verbal-style sentence, then `Chunk` and `Meaning`.

The direction was inverted by [0050](../decisions/0050-show-the-nvv-sentence-on-the-front-of-the-transformation-card.md). The field names still describe the original direction (verbal prompt, nominal answer); only the templates swap them, so the fields and existing notes are unchanged. A collection created before 0050 keeps the old templates until they are replaced once in Anki.

When the NVV has no direct verb, `Prompt` uses the closest plain paraphrase (*wirksam werden* for *in Kraft treten*).

## Tags

Every note gets:

- `learn-german`
- `provider::<name>`, for example `provider::anthropic`
- `model::<id>`, for example `model::claude-opus-5-5`
- `run::<run-id>`, for example `run::run-20261124-1530`

Anki splits tags on whitespace, so whitespace inside a provider or model name becomes `_`. `NoteBuilder` in `application/notes/` builds the fields and tags.

## Versioning

The version is part of the note type name (`-v1`). A field change creates the next version and migrates existing notes into it; the old type is removed once empty.

The v1 field names and order are asserted literally in `tests/unit/notes/test_note_type_specs.py`, so a field change fails CI until the new version exists. If a note type in Anki has other fields than the tool's, `ensure_setup` stops with `NoteTypeMismatchError` instead of adding notes.

## Related

- [Requirements](../product/requirements.md)
- [0006 Card types](../decisions/0006-use-transformation-and-translation-prompt-cards.md)
- [0012 Card content](../decisions/0012-make-both-cards-practise-the-chunk.md)
- [0049 Drop the translation card](../decisions/0049-drop-the-translation-card-and-the-hint-language.md)
- [AnkiConnect](../integrations/ankiconnect.md)

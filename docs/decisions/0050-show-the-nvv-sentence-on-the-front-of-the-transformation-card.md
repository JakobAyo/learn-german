---
title: Show the NVV sentence on the front of the transformation card
summary: The transformation card is inverted; the front shows the sentence with the NVV and asks for a verbal rewrite. Only the templates change, not the fields.
status: active
updated: 2026-11-27
---

# Show the NVV sentence on the front of the transformation card

## Context

[0012](0012-make-both-cards-practise-the-chunk.md) put the verbal-style rewrite on the front of the transformation card and asked the learner to produce the nominal-style sentence with the NVV. After reviewing the first v1 cards in Anki, the owner wants the direction inverted: read the sentence as it appeared in the source, with the NVV, and restate it in plain verbal style.

## Decision

- **Front:** "Rewrite in verbal style, without the NVV:" followed by the shortened source sentence (field `Answer`).
- **Back:** the front, a line, the verbal-style sentence (field `Prompt`), then `Chunk` in bold and `Meaning` in italics.
- **Only the templates change.** The note type keeps its name `learn-german-transformation-v1` and its fields, so no migration is needed and the LLM output, prompt version `card-v2` and cache are unchanged. The field names `Prompt` and `Answer` now describe the old direction: `Answer` is shown on the front and `Prompt` on the back. Renaming them would need a `-v2` note type and a migration of the existing notes, which the swap does not justify.

## Alternatives considered

- **A second card template on the same note type, one per direction:** practises both directions, but doubles the reviews per chunk, which is what [0049](0049-drop-the-translation-card-and-the-hint-language.md) removed.
- **A `-v2` note type with renamed fields (`Front`, `Back`):** clearer names, but it needs a migration of every existing note for a purely cosmetic gain.

## Consequences

- The card now trains understanding of the NVV and paraphrasing it, rather than producing it from a verbal sentence. The learner still meets the chunk in context and sees it with its meaning on the back.
- `ensure_setup` never edits an existing note type ([0038](0038-create-missing-note-types-and-check-only-their-fields.md)), so a collection that already has `learn-german-transformation-v1` keeps the old direction until its templates are replaced once: in Anki, Tools, Manage Note Types, `learn-german-transformation-v1`, Cards, paste the new front and back from `src/learn_german/adapters/anki/templates/`. A fresh collection gets the new templates from `ensure_setup`.
- The golden rendering in `tests/data/anki/transformation_v1.golden.html` pins the new direction.

## Related

- [Note types](../learning-design/note-types.md)
- [Requirements](../product/requirements.md)
- [0012 Card content](0012-make-both-cards-practise-the-chunk.md)

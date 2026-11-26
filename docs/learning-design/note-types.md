---
title: Note types
summary: Deck, the two v1 note types and their fields, card fronts and backs, and tags; fields are hard to change once notes exist.
status: active
updated: 2026-11-26
---

# Note types

## Purpose

Defines what v1 puts into Anki: the deck, the two note types, their fields and what each card shows. Changing a field after notes exist needs a migration (see [0003](../decisions/0003-push-notes-live-through-ankiconnect.md)), so read this before touching the export or the generation prompt. The content rules come from [0012](../decisions/0012-make-both-cards-practise-the-chunk.md).

## Deck

`learn-german::chunks` by default, configurable. The tool only adds notes to this deck and never touches other decks.

## Shared fields

Both note types start with the same fields, in this order. `ChunkKey` is first because Anki checks duplicates on the first field within a note type.

| Field | Example | Source |
|---|---|---|
| `ChunkKey` | `entscheidung\|treffen` | extractor ([0011](../decisions/0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)) |
| `Chunk` | eine Entscheidung treffen | LLM, citation form ([0028](../decisions/0028-let-the-llm-supply-the-citation-form.md)) |
| `Meaning` | eine Entscheidung treffen = entscheiden, sich festlegen | LLM, one line in German |
| `Answer` | Die Regierung hat die Entscheidung getroffen, die Steuer zu senken. | LLM, shortened source sentence |

`ChunkKey` is not shown on any card.

## Transformation note type: `learn-german-transformation-v1`

Extra field:

| Field | Example |
|---|---|
| `Prompt` | Die Regierung hat entschieden, die Steuer zu senken. |

- **Front:** "Rewrite in nominal style, using an NVV:" followed by `Prompt`.
- **Back:** `Answer`, then `Chunk` and `Meaning`.

When the NVV has no direct verb, `Prompt` uses the closest plain paraphrase (*wirksam werden* for *in Kraft treten*).

## Translation-prompt note type: `learn-german-translation-v1`

Extra fields:

| Field | Example |
|---|---|
| `Prompt` | The government made the decision to lower the tax. |
| `HintLanguage` | en |

- **Front:** `Prompt`, then "Use: " followed by `Chunk`.
- **Back:** `Answer`, then `Meaning`.

`HintLanguage` records which language the prompt is in, so a later change of the setting can be told apart from old notes.

## Tags

Every note gets:

- `learn-german`
- `provider::<name>`, for example `provider::anthropic`
- `model::<id>`, for example `model::claude-opus-5-5`
- `run::<run-id>`, for example `run::run-20261124-1530`

## Versioning

The version is part of the note type name (`-v1`). A field change creates the next version and migrates existing notes into it; the old type is removed once empty.

## Related

- [Requirements](../product/requirements.md)
- [0006 Card types](../decisions/0006-use-transformation-and-translation-prompt-cards.md)
- [0012 Card content](../decisions/0012-make-both-cards-practise-the-chunk.md)

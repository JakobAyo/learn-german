---
title: Drop the translation card and the hint language
summary: Each chunk now gets one transformation note; the translation-prompt note type, the translation field and the hint_language setting are removed.
status: active
updated: 2026-11-27
---

# Drop the translation card and the hint language

## Context

[0006](0006-use-transformation-and-translation-prompt-cards.md) chose two production card types, and [0012](0012-make-both-cards-practise-the-chunk.md) gave every chunk one note of each. After the release check of v1 the owner decided the translation prompt is not worth having: it doubles the cards per chunk, and a chunk the learner does not know can simply be looked up. The transformation card already makes the learner produce the chunk in a German sentence, so the second review of the same chunk costs study time without training much that is new. The translation card was also the only reason for the hint language setting ([0015](0015-set-v1-run-defaults.md), R16), which every user had to set before the first `sync`.

## Decision

- **One note per chunk:** the transformation note (`learn-german-transformation-v1`). `NoteKind` has one member, `TRANSFORMATION`. The cap still counts chunks, so `--cap 3` now adds 3 notes.
- **The translation card is removed:** the `learn-german-translation-v1` note type, its templates, `CardContent.translation` and the `translation` field of the LLM output schema.
- **The hint language is removed:** the `hint_language` setting, `LEARN_GERMAN_HINT_LANGUAGE`, the "No hint language is set" check of `sync`, `CardRequest.hint_language` and `run_eval.py --hint-language`. `sync` now checks only the API key before it opens the database ([0046](0046-check-settings-and-anki-before-selecting-and-keep-dry-runs-read-only.md)).
- **New prompt version `card-v2`**, the `card-v1` template without the translation field. The cache key no longer includes a hint language; `card-v1` answers are not reused.
- **Migration 0002** deletes the `pushed_notes` rows whose `note_kind` is `translation`, so stored progress parses and a chunk's status depends on its transformation note alone.
- **The machinery for several note kinds stays:** `ChunkStatus.PARTIAL`, the partial-first ranking of [0034](0034-rank-partial-chunks-first-then-by-occurrences.md) and the per-kind deduplication are generic over `NoteKind`. With one kind no chunk is partial, but a later card type can be added as a new kind without rebuilding them.

## Alternatives considered

- **Keep the translation card behind a setting, off by default:** an extra setting, code path and set of tests for a card the tool's one user does not want. If it is wanted again, it can come back as a new note kind, since the multi-kind machinery stays.
- **Keep the hint language for the `Meaning` field:** `Meaning` is a German explanation by design, so the learner stays in German on the back of the card; it never used the hint language.

## Consequences

- Half as many notes and LLM output tokens per chunk; a `sync --cap N` adds N notes.
- A `config.toml` that still sets `hint_language` now fails as an unknown setting ([0024](0024-read-settings-with-pydantic-settings.md)); delete that line. `LEARN_GERMAN_HINT_LANGUAGE` in the environment or `.env` is ignored.
- Translation notes already in an Anki collection are left alone: the tool no longer reads, counts or deletes them. Delete the `learn-german-translation-v1` note type in Anki to remove them.
- Existing transformation notes stay valid, because their note type is unchanged.
- The card quality measurement grades one note per chunk ([Card quality of v1](../research/card-quality-v1.md)).

## Related

- [Note types](../learning-design/note-types.md)
- [Generation](../system-design/generation.md)
- [Configuration](../development/configuration.md)
- [Requirements](../product/requirements.md)

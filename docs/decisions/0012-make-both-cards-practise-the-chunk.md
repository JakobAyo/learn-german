---
title: Make both cards practise the chunk, two notes per chunk
summary: Both cards drill the chunk on a shortened sentence; one note of each type per chunk, and the cap counts chunks.
status: active
updated: 2026-11-24
---

# Make both cards practise the chunk, two notes per chunk

## Context

[0006](0006-use-transformation-and-translation-prompt-cards.md) chose two card types but left their content open. Most sentences that contain an NVV have no participial attribute to rewrite. Many NVVs have no direct verb equivalent (*in Kraft treten*). News sentences are often longer than 30 words. [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md) capped "new notes" without saying whether one chunk means one note or two.

## Decision

- **One chunk, two notes.** Every selected chunk gets one transformation note and one translation-prompt note. Both carry the same chunk key. Deduplication checks each note type separately: a note is created only if no note of that type has the key, so a chunk missing one of its notes gets just that note.
- **The cap counts chunks.** A cap of 10 means 10 chunks, which is 20 notes. This refines 0009.
- **Shortened base sentence.** The LLM shortens the source sentence to the clause around the chunk, about 10 to 20 words, keeping the chunk and its meaning. Both cards are built on this shortened German sentence.
- **Transformation is chunk-centred only.** The front shows the base sentence rewritten in verbal style, and the learner produces the nominal-style sentence with the NVV. When the NVV has no direct verb, the LLM uses the closest plain paraphrase (*wirksam werden* for *in Kraft treten*). The participial attribute to relative clause rewrite from 0006 is dropped for v1.
- **Translation prompt names the chunk.** The front shows the base sentence translated into the hint language, plus the chunk to use (*Use: eine Entscheidung treffen*). The back shows the German base sentence.
- **German meaning on the back.** Both notes carry a one-line German explanation of the chunk (*in Kraft treten = gültig werden*), generated in the same LLM call.
- The source title, link and surrounding sentences are not put on cards. They stay in SQLite.

## Alternatives considered

- LLM picks the transformation per sentence, or adds a syntax transformation card when possible: rejected, because some cards would not practise the chunk.
- Skip the transformation card, or the whole chunk, when no direct verb exists: rejected, because it drops many idiomatic NVVs.
- Full original sentence, or a newly written example sentence: rejected. The first makes cards heavy, and the second loses the link to what the learner read.
- One card type per chunk, or the cap counting notes: rejected in favour of practising each chunk both ways.
- Only the noun, or no hint, on the translation front: rejected, because a correct answer without the chunk could not be graded fairly.
- Source link, context sentences or a register note on the back: not chosen; they can be added later as new fields through a note type migration.

## Consequences

- One LLM call per chunk can return the shortened sentence, the verbal-style rewrite, the translation and the meaning as one structured result.
- Paraphrase fronts are looser than strict verb equivalents. This is part of the quality question in [0005](0005-push-cards-automatically-with-tagging-and-dry-run.md).
- Syntax transformations (participial attribute, relative clause) can return later as their own note type.
- Field layout is in [Note types](../learning-design/note-types.md).

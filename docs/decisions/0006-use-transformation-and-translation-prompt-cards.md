---
title: Use transformation and translation-prompt cards, not chunk cloze
summary: v1 builds two production card types, sentence transformation and translation prompt, and drops the chunk cloze proposed in the DeepSeek chat.
status: active
updated: 2026-11-27
---

# Use transformation and translation-prompt cards, not chunk cloze

> **Amended by [0049](0049-drop-the-translation-card-and-the-hint-language.md)** (2026-11-27). The translation-prompt card is dropped; v1 builds only the sentence-transformation card. Dropping the chunk cloze still holds.

## Context

The [DeepSeek chat](../research/deepseek-chat-advice.md) proposed a chunk cloze as the first card type, with transformation cards second. The [learning goals](../product/learning-goals.md) favour production over recognition, and want vocabulary and sentence building practised together.

## Decision

v1 builds two card types:

- **Transformation:** a sentence containing the chunk is rewritten (verbal to nominal style, participial attribute to relative clause, and the reverse), with a model answer.
- **Translation prompt:** a sentence in the configured hint language is given, and the learner produces the German sentence using the chunk.

Chunk cloze is not built. The hint language is configurable.

## Alternatives considered

- Chunk cloze first: rejected by the owner. It would have allowed a v1 without an LLM, but trains a narrower skill.
- Audio on cards: deferred. It needs a TTS provider, which would go behind its own interface.

## Consequences

- An LLM is needed from the first usable version (see [0004](0004-generate-card-content-through-a-pluggable-llm-provider.md)).
- Each card type is its own note type, so more types (cloze included) can be added later without changing existing notes.
- Card layouts and what each trains belong in `learning-design/`.

Card content is refined in [0012](0012-make-both-cards-practise-the-chunk.md): the participial attribute to relative clause rewrite is dropped for v1.

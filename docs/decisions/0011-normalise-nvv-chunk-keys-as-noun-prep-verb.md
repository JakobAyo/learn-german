---
title: Normalise NVV chunk keys as noun, preposition, verb
summary: An NVV's permanent key is the lemmas of noun, preposition, optional sich, and verb, joined by |, without articles or negation.
status: active
updated: 2026-11-24
---

# Normalise NVV chunk keys as noun, preposition, verb

## Context

Deduplication relies on a normalised chunk key, and that key is effectively permanent once notes exist (see [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)). 0009 gave only the example `entscheidung|treffen`. It left open how to handle prepositions, articles, contractions, reflexives and negation. Some NVVs differ only in the preposition: *in Frage stellen* (to question) and *eine Frage stellen* (to ask a question) are different chunks.

## Decision

The key for a Nomen-Verb-Verbindung is built from lowercase lemmas joined by `|`, in this order:

1. the noun;
2. the preposition, if the noun is governed by one; contractions are expanded (*zur* → `zu`, *im* → `in`, *zum* → `zu`);
3. `sich`, if the verb is reflexive in this chunk;
4. the verb, in its infinitive form, without any separable prefix that belongs to a different verb.

Articles, determiners, adjectives, negation (*nicht*, *kein*) and tense are dropped.

| Surface form | Key |
|---|---|
| zur Verfügung stellen | `verfügung\|zu\|stellen` |
| zur Verfügung stehen | `verfügung\|zu\|stehen` |
| in Frage stellen | `frage\|in\|stellen` |
| eine Frage stellen | `frage\|stellen` |
| keine Rolle spielen | `rolle\|spielen` |
| sich in Acht nehmen | `acht\|in\|sich\|nehmen` |
| traf eine Entscheidung | `entscheidung\|treffen` |

Spelling variants that are written as one word (*infrage stellen*) are mapped to the separate form (`frage|in|stellen`) by a small variant table, which is kept in a data file.

## Alternatives considered

- Noun and verb only: rejected, because different chunks collide (*in Frage stellen* and *eine Frage stellen*), and the second is never carded.
- The whole lemmatised phrase: rejected, because word order and spelling variants create near-duplicates.

## Consequences

- The key is stored in its own note field, the first field of each note type (see [Note types](../learning-design/note-types.md)).
- Lemmatisation errors by spaCy produce wrong keys. The extractor's tests must cover the table above.
- Changing the format later needs a migration of every existing note.

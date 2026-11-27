---
title: Let the LLM supply the citation form of a chunk
summary: The Chunk field comes from the LLM as CardContent.citation_form, not the extractor, because the citation article is not in the parse.
status: active
updated: 2026-11-26
---

# Let the LLM supply the citation form of a chunk

## Context

The `Chunk` field of both note types shows the chunk in citation form, for example *eine Entscheidung treffen*, *zur Verfügung stellen* or *Abschied nehmen* ([Note types](../learning-design/note-types.md)). The [Roadmap](../product/roadmap.md) left it to M2 to derive this from the parse, or to move it to the LLM in M5 if that is unreliable. M5 and M6 both depend on `CardContent`, so the question had to be settled before the tracks started in parallel ([0026](0026-run-m2-m4-m5-m6-as-parallel-tracks.md)).

The parse cannot give the citation article: the source sentence may say *die Entscheidung*, *keine Entscheidung* or *Entscheidungen*, and whether the citation form has an article at all (*eine Entscheidung treffen* but *Abschied nehmen*) is a convention of the language, not of the sentence.

## Decision

- `CardContent` has a `citation_form` field. The LLM returns it with the rest of the card content, and the note builder puts it into `Chunk`.
- `Candidate` keeps no citation form, so M2 does not change the candidates table.

## Alternatives considered

- **Derive it from the parse with gender and a rule for the article:** cannot tell chunks without an article from those with one, and fails on plurals and negation.
- **A hand-written citation table:** precise, but every new chunk needs a manual entry.

## Consequences

- The citation form costs no extra LLM call; it is one more field in the same response.
- M5's sanity checks should verify that the citation form contains the key's noun and verb lemmas, so a wrong chunk is caught as a `GenerationError`.

## Related

- [0011 Normalise NVV chunk keys](0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)
- [0012 Make both cards practise the chunk](0012-make-both-cards-practise-the-chunk.md)

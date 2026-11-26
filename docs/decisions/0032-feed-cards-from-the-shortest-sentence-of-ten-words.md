---
title: Feed the cards from the shortest sentence of at least ten words
summary: Of a chunk's occurrences, the picker takes the shortest sentence with at least ten words, else the longest; ties go to the most recent occurrence.
status: active
updated: 2026-11-26
---

# Feed the cards from the shortest sentence of at least ten words

## Context

A chunk key usually has several occurrences across sources, and `sync` sends one sentence and its context to the LLM ([0012](0012-make-both-cards-practise-the-chunk.md)). [Pipeline](../system-design/pipeline.md) left open which one. The LLM shortens the sentence to the clause around the chunk, about 10 to 20 words. A long sentence makes that shortening harder and more likely to drift from the source, while a very short sentence (a headline, a fragment) gives a thin card and can fall below the length M5's sanity check expects. The [Roadmap](../product/roadmap.md) recommended the shortest sentence within a word range, most recent on ties.

## Decision

- The `OccurrencePicker` port takes a chunk's occurrences, oldest first, and returns one. The v1 strategy is `ShortestSentencePicker` in `application/selection/picker.py`.
- It picks the **shortest sentence with at least 10 words**. If every sentence is shorter, it picks the **longest**. Ties go to the **most recent** occurrence, the one stored last.
- A word is a whitespace-separated token with at least one letter or digit, so a lone dash does not count.
- The minimum is a constructor argument with the default 10, the low end of the shortened sentence in 0012. It is not a user setting.
- The picked occurrence's sentence and context go into the `CardRequest`.

The roadmap's range has no upper bound here: once the shortest qualifying sentence wins, an upper limit would never change the choice, only the fallback when no sentence qualifies, and there the longest short sentence is the better card.

## Alternatives considered

- **Shortest sentence overall:** prefers headlines and fragments, and sentences shorter than the card should be.
- **Closest to a target length (say 15 words):** similar result, but needs a second number and treats a 12-word and an 18-word sentence as equally good, although the shorter needs less rewriting.
- **Most recent occurrence:** matches what the learner read last, but ignores length, which matters more for card quality.
- **Let the LLM choose among all occurrences:** more tokens per call, and the cache key would change with every new occurrence, not only when a better sentence arrives.

## Consequences

- Adding a new source can change the picked sentence of a pending chunk, so its cached LLM output no longer matches and the next `sync` pays again. Chunks that are already pushed are not affected.
- When every occurrence is under ten words, the LLM gets a short sentence and may return one under ten words. M5's length check must allow a shortened sentence that is no longer than its source, or such a chunk fails on every run.
- Recency is insertion order, not the source's fetch time, so a `reextract` that finds an occurrence again in an old source counts it as recent.

## Related

- [Pipeline](../system-design/pipeline.md)
- [0012 Make both cards practise the chunk](0012-make-both-cards-practise-the-chunk.md)

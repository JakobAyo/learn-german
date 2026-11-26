---
title: Check card content cheaply, then cache it per request in its own transaction
summary: CheckedProvider turns clearly wrong content into a GenerationError; CachingProvider wraps it, keyed by a request hash, in its own transactions.
status: active
updated: 2026-11-26
---

# Check card content cheaply, then cache it per request in its own transaction

## Context

There is no review step, so a wrong card reaches the deck ([0005](0005-push-cards-automatically-with-tagging-and-dry-run.md)). A schema only says that five strings came back, not that they fit the chunk. The [Roadmap](../product/roadmap.md) asks for cheap checks beyond the schema and for a caching decorator around any provider, so that a request is never paid for twice ([0004](0004-generate-card-content-through-a-pluggable-llm-provider.md), [0014](0014-keep-progress-when-a-run-fails-partway.md)). Two questions were open: whether content that fails a check is cached, and which transaction the cache writes in. `sync` runs one unit-of-work block per chunk; if the cache wrote inside it, a rejected push would roll the paid answer back.

## Decision

- **Two decorators in `application/generation/`, wired as `CachingProvider(CheckedProvider(provider), uow, clock)`.** Both pass `name`, `model` and `prompt_version` through. Only content that passed the checks is cached.
- **The checks** (`checks.py`), each failure a `GenerationError` naming every problem, so the chunk stays pending:
  - The shortened sentence contains the key's noun, compared case-insensitively with umlauts folded, so *Anträge* matches *antrag* and *infrage* matches *frage*.
  - The shortened sentence has 8 to 25 words, counted like the picker ([0032](0032-feed-cards-from-the-shortest-sentence-of-ten-words.md)). The prompt asks for 10 to 20; the check allows a margin. If the source sentence has fewer than 10 words, the picker had no longer one, so the shortened sentence only has to be no longer than the source.
  - The citation form contains the key's noun and verb ([0028](0028-let-the-llm-supply-the-citation-form.md)).
  - The meaning is one line.
- **The cache key** is the SHA-256 of canonical JSON (sorted keys, no extra whitespace) holding provider, model, prompt version, and the request's key, kind, sentence, context and hint language.
- **The cached value** is the checked `CardContent` as JSON, not the provider's raw response, so the decorator works for any provider. An entry that no longer decodes into `CardContent` is a miss and is overwritten.
- **Own transactions.** `CachingProvider` reads in one short `with uow:` block and writes in another, around the call. A later failure of the chunk does not undo the cache write, and the database is not locked during the network call. `generate` must therefore be called outside any `with uow:` block, like `ChunkSelector.select`.

## Alternatives considered

- **Cache before checking:** a chunk whose answer fails a check would fail from the cache on every run until the check changed, with no chance of a better answer.
- **Cache inside the chunk's transaction:** a failed push rolls back the paid answer, and the SQLite write lock is held through a slow API call.
- **Checks inside `AnthropicProvider`:** every future provider would repeat them.
- **A strict 10-to-20-word range:** rejects usable sentences one or two words off. **Checking the verb in the shortened sentence:** needs a lemmatiser, since it is inflected (*traf* for *treffen*).
- **Checking that the verbal rewrite avoids the noun:** rejects good rewrites such as *beantragen* for *einen Antrag stellen*.

## Consequences

- A chunk whose answers keep failing the checks costs one call per `sync`. The retry limit that [0014](0014-keep-progress-when-a-run-fails-partway.md) foresees would bound it.
- Changing a check does not invalidate cached content, which already passed the old checks.
- The checks catch clearly wrong output only; the error rate of subtly wrong cards still needs measuring once v1 runs.
- M7 wires the decorators in `bootstrap.py` and calls `generate` before opening the chunk's unit of work.

## Related

- [Generation](../system-design/generation.md)
- [0035 Version the card prompt](0035-version-the-card-prompt-as-a-template-with-a-pinned-hash.md)

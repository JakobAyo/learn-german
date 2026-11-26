---
title: Version the card prompt as a template file with a pinned hash
summary: The card prompt is a template file beside the LLM adapters with a pure renderer; PROMPT_VERSION is in every cache key, and a test pins its hash.
status: active
updated: 2026-11-26
---

# Version the card prompt as a template file with a pinned hash

## Context

Every chunk's card content comes from one LLM call ([0012](0012-make-both-cards-practise-the-chunk.md)), and identical requests are answered from a cache keyed by provider, model, prompt version and input ([0004](0004-generate-card-content-through-a-pluggable-llm-provider.md)). If the prompt changes but its version does not, the cache keeps serving answers to the old prompt. The [Roadmap](../product/roadmap.md) asks for the prompt as a template file plus a `PROMPT_VERSION`, rendered by a pure function. [Parallel tracks](../development/parallel-tracks.md) listed rendering under `application/generation/` and the template under `adapters/llm/`, but import-linter makes `application` and `adapters` independent layers, so an adapter cannot call a renderer in `application`.

## Decision

- **Template file:** `adapters/llm/prompts/card_v1.md`, loaded through `importlib.resources`. It is the single user message of the call; there is no system prompt.
- **Rendering next to the template:** `render_prompt(template, request)` in `adapters/llm/prompt.py` is a pure function using `string.Template`. It inserts the chunk key, the source sentence, the context (or `(none)`) and the hint language's ISO 639 code. Every LLM adapter in `adapters/llm/` uses it, so a later DeepSeek or `claude -p` adapter sends the same prompt.
- **What the prompt asks for:** the five `CardContent` fields, each on one line: the citation form ([0028](0028-let-the-llm-supply-the-citation-form.md)); the sentence shortened to 10 to 20 words, kept as it is and never made longer when it has fewer than 10 words ([0032](0032-feed-cards-from-the-shortest-sentence-of-ten-words.md)); the verbal-style rewrite with a single verb or the closest plain paraphrase; the translation; and the meaning as "citation form = explanation".
- **`PROMPT_VERSION = "card-v1"`** in `adapters/llm/prompt.py`. `LLMProvider` gains a `prompt_version` property, so the caching decorator reads it from whatever provider it wraps.
- **Two tests guard the version.** A golden file (`tests/data/llm/card_v1_prompt.golden.txt`) holds one rendered prompt. `tests/data/llm/prompt_hashes.json` holds the template's SHA-256 per version; the test fails when the current template does not match the hash recorded for `PROMPT_VERSION`.
- **Changing the prompt** means a new template file, a new `PROMPT_VERSION`, a new hash entry and an updated golden file, all by hand.

## Alternatives considered

- **Rendering in `application/generation/`, as the track list said:** the adapter could not import it, so bootstrap would have to inject a render function into each provider. More wiring for no gain; the prompt belongs with the adapters that send it.
- **The template's hash as the version:** invalidates the cache on its own, but also on a whitespace fix, and the version stored in `llm_cache` rows would be an opaque hash. An explicit name with a test that enforces the bump keeps changes visible in review.
- **The prompt as a Python string constant:** harder to read and review than a Markdown file.
- **Jinja:** a new dependency for four substitutions.

## Consequences

- A prompt change re-generates every pending chunk once, at full cost. Chunks already pushed are not affected.
- `string.Template` leaves `$` inside the inserted sentence alone, so sentences with prices render as written.
- [Code architecture](../system-design/code-architecture.md) shows `adapters/llm/` with `caching.py`; the cache lives in `application/generation/` instead ([0036](0036-check-card-content-then-cache-it-in-its-own-transaction.md)).

## Related

- [Generation](../system-design/generation.md)
- [Claude API](../integrations/claude-api.md)

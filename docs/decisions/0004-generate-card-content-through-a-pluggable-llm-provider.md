---
title: Generate card content through a pluggable LLM provider, Claude API first
summary: Translations and model answers come from an LLM provider interface; the Claude API is the first adapter, with claude -p and DeepSeek addable later.
status: active
updated: 2026-11-24
---

# Generate card content through a pluggable LLM provider, Claude API first

## Context

Both v1 card types need generated content: a translation for translation-prompt cards and a model answer for transformation cards (see [0006](0006-use-transformation-and-translation-prompt-cards.md)). The owner has access to the Claude API, the DeepSeek API, and a Claude subscription that can run `claude -p` headless. The provider may change.

## Decision

- All generation goes through one provider interface: a typed request in, structured output out.
- The Claude API (Anthropic SDK, `ANTHROPIC_API_KEY`) is the first and main adapter.
- A headless `claude -p` adapter may be added for testing without API cost. A DeepSeek adapter may follow. The provider is chosen by config.
- Responses are cached in SQLite, keyed by provider, model, prompt version and input, so identical requests are never paid for twice.
- No separate spending limit. The per-run new-note cap bounds cost (see [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)).

## Alternatives considered

- A single hard-wired provider: rejected, because the owner expects to switch.
- A local model only: rejected for v1, because it is weaker at German transformations.
- No LLM: rejected, because neither v1 card type can be built without generated content.

## Consequences

- Prompts are versioned, so the cache invalidates when a prompt changes.
- Provider name and model are written to each note as tags (see [0005](0005-push-cards-automatically-with-tagging-and-dry-run.md)).
- Tests use a fake provider. CI never calls a real one.

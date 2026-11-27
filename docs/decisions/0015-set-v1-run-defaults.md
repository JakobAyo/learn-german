---
title: Set v1 run defaults, Claude Opus 5.5, ten chunks, required hint language
summary: The default model is Claude Opus 5.5, the default cap is 10 chunks per run, and there is no default hint language; the user must set one.
status: active
updated: 2026-11-27
---

# Set v1 run defaults, Claude Opus 5.5, ten chunks, required hint language

> **Amended by [0049](0049-drop-the-translation-card-and-the-hint-language.md)** (2026-11-27). The hint language setting no longer exists, so there is nothing to set. The default model and the default cap still hold.

## Context

[0004](0004-generate-card-content-through-a-pluggable-llm-provider.md) chose the Claude API but no model. [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md) made the cap configurable but gave no default. The requirements made the hint language a setting without a default.

## Decision

- **Model:** `claude-opus-5-5` is the default for the Claude API adapter. It is a config setting.
- **Cap:** 10 chunks per run by default, which is 20 notes (see [0012](0012-make-both-cards-practise-the-chunk.md)). This matches Anki's default of 20 new cards per day.
- **Hint language:** no default. The tool refuses to generate cards until a hint language is set in config, and says how to set it. `--dry-run` also requires it, since it runs generation.

## Alternatives considered

- Claude Sonnet 5.5 as default: rejected. It costs about half as much, but a wrong model answer trains the error, and with no review step quality matters more than a few cents per run.
- Claude Haiku 5.5 as default: rejected for real cards. It remains a cheap choice for testing.
- A cap of 5 or 20 chunks: 10 fits one day of new cards at Anki's defaults.
- English as default hint language: rejected, so the tool never quietly uses a language the user did not choose.

## Consequences

- A rough cost is a few tenths of a dollar per run of 10 chunks. Measure real cost once v1 runs.
- First-time setup must include setting the hint language. The setup guide in `development/` must say so.

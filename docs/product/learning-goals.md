---
title: Learning goals
summary: B2 to C1 goal, the two core weaknesses (word finding, error-free sentences) and why Anki is the study channel.
status: active
updated: 2026-11-23
---

# Learning goals

## Purpose

Records what the learner wants from this project and why. Every feature, card type and data source should trace back to a goal here. Read this before proposing scope.

## Current level

Self-assessed between B2 and C1. Progress has stalled: more exposure alone has not produced measurable improvement.

## Core weaknesses

1. **Word finding (active vocabulary).** In the learner's words: "I use the same words for everything and speak basic German." They understand far more than they produce, and the precise word or fixed phrase does not come to mind.
2. **Sentence building.** Sentences contain mistakes and stay simple. At this level the gap is expression quality and register as much as correctness: nominal style, extended participial attributes and formal prepositions (see [DeepSeek chat advice](../research/deepseek-chat-advice.md)). Which specific errors recur has not been measured yet.

## Goal

Reach a solid C1 as efficiently as possible. Efficiency beats breadth: study time goes to items that close a known gap, not to material the learner already masters.

## Study channel

- **Anki with spaced repetition is the primary study channel.** The project's job is to extract and prepare material so the learner does not spend time building cards by hand.
- **Reading books is a separate, free-time activity.** It is not something the tool must replace or schedule. Books may still serve as input sources later.

## What this means for the extractor

- Prefer cards that force **production** (German answer from a prompt or context) over recognition (German to translation).
- Prefer **chunks in context** (Nomen-Verb-Verbindungen such as *eine Entscheidung treffen*, set phrases, full example sentences) over isolated word lists, because word finding fails at the level of usage, not definition.
- Train sentence building through **transformation exercises** on the same cards, so vocabulary and grammar are practised together.
- Skip what the learner already knows, so that every review earns its time.

## Open questions

- Which input sources come first: news articles, video subtitles, or both? See `data/` once decided.
- Should the learner's own corrected writing become a source later? It would be the most direct evidence of a gap, but neither the learner nor the DeepSeek chat has asked for it yet.
- How is "already known" measured: a frequency cut-off, an imported known-words list, or the existing Anki collection?
- What daily review budget is sustainable? See `learning-design/`.

## Related

- [DeepSeek chat advice](../research/deepseek-chat-advice.md): the outside advice this project started from
- [0001 Adopt a concern-based documentation structure](../decisions/0001-adopt-documentation-structure.md)

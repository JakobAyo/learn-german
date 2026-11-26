---
title: System design
summary: Extraction pipeline: ingest, NLP processing, filtering and ranking, card generation, export.
---

# System design

Extraction pipeline: ingest, NLP processing, filtering and ranking, card generation, export.

## What belongs here

- Pipeline stages and component boundaries
- Filtering and ranking logic (frequency, known words, level)
- Data flow from source to card

## What does not belong here

- Details of individual input sources (data/)
- External API quirks (integrations/)
- Local setup and commands (development/)

<!-- docs-index:start -->

## Contents

- [Code architecture](code-architecture.md) `[draft]` — Ports-and-adapters layout of the Python package, the dependency rule, every port with its v1 adapter and fake, and the patterns used where.
- [Generation](generation.md) — How a CardRequest becomes checked, cached CardContent: provider port, versioned prompt, sanity checks, cache decorator and wiring.
- [NVV extraction](nvv-extraction.md) — How the NVV extractor parses with spaCy, matches light verbs in ranked tiers, builds 0011 keys and context, and how its quality is guarded.
- [Pipeline](pipeline.md) — Stages from source to Anki note, which command (add or sync) owns each, and what each stage reads from and writes to SQLite.

<!-- docs-index:end -->

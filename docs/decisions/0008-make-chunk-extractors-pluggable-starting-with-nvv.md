---
title: Make chunk extractors and source adapters pluggable, starting with NVV
summary: Extraction and ingest are plug-in interfaces; v1 ships the Nomen-Verb-Verbindung extractor and the news-URL and local-file sources.
status: active
updated: 2026-11-24
---

# Make chunk extractors and source adapters pluggable, starting with NVV

## Context

The first chunk kind is the Nomen-Verb-Verbindung, but formal prepositions, verbs with fixed prepositions, and collocations and idioms are wanted later. The first sources are news article URLs and local files; YouTube subtitles and the learner's own writing may follow.

## Decision

- **Extractors** share an interface: parsed document in, candidate chunks out (chunk key, kind, sentence, context). v1 ships only the NVV extractor, built on the spaCy dependency parse with a light-verb whitelist.
- **Source adapters** share an interface: a reference (URL or path) in, plain text plus metadata out. v1 ships a news-article adapter and a local `.txt` adapter.
- The pipeline is ingest, parse, extract, filter, rank, generate, export. Each stage has its own seam, so the deferred filter and extra ranking signals slot in without restructuring.

## Alternatives considered

- A single hard-coded NVV extractor: rejected, because three more kinds are already planned.
- Adjacent POS patterns, as the DeepSeek chat suggested: rejected, because German verb brackets split the noun from the verb.

## Consequences

- Text is parsed once per document and shared by all extractors.
- Each extractor defines its own normalised chunk key, which deduplication relies on (see [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)).

---
title: Normalise source text by paragraph before hashing
summary: Source text is NFC with blank-line paragraphs and collapsed whitespace; the content hash is its SHA-256, and files are stored by absolute path.
status: active
updated: 2026-11-26
---

# Normalise source text by paragraph before hashing

## Context

R6 recognises a source by its content hash, and the roadmap asks for the SHA-256 of the normalised text without defining "normalised". Too little normalisation lets the same article saved twice with other line wrapping count as new; too much loses the paragraph breaks the spaCy parser uses to batch text ([NVV extraction](../system-design/nvv-extraction.md)). The two adapters also produce text in different shapes: trafilatura puts one paragraph per line, while a hand-saved `.txt` file often wraps lines inside a paragraph.

## Decision

- `normalise_text` in `adapters/sources/text.py` is shared by every source adapter: Unicode NFC, paragraphs split at blank lines, every other run of whitespace (line breaks, tabs, no-break spaces) collapsed to one space, paragraphs joined by one blank line, empty paragraphs dropped.
- The news adapter first turns each line of trafilatura's output into its own paragraph, then normalises.
- The content hash is the SHA-256 hex digest of the normalised text in UTF-8. The normalised text is what is stored and extracted.
- A local file is read as UTF-8 with an optional byte-order mark; any other encoding fails with a message to save it as UTF-8. Its reference is the absolute path, its title the file name without the suffix. A file with no text after normalising fails.

## Alternatives considered

- **Hash the raw bytes:** a re-saved file with other line endings or wrapping would be a new source.
- **Collapse all whitespace, paragraphs included:** simpler hash, but the stored text loses its paragraphs.
- **Case-folding or stripping punctuation before hashing:** would merge texts that differ in content; not worth the risk for a duplicate check.
- **Guess the encoding of local files:** guesses go wrong silently on German umlauts; a clear error is cheaper.

## Consequences

- The same article from two URLs is recognised only if trafilatura extracts the same text from both pages, which holds for mirrors but not for different layouts.
- Changing the normalisation changes every hash, so stored sources would no longer match their re-fetched text. Treat it as a migration.

## Related

- [Ingest](../system-design/ingest.md)
- [0042 Recognise known sources before fetching](0042-recognise-known-sources-before-fetching-and-refresh-them-in-place.md)

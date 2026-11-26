---
title: Ingest
summary: How add, status and reextract work: source adapters, normalising and hashing, polite fetching, duplicate checks, --force, the 0017 rules, output, exit codes.
status: active
updated: 2026-11-26
---

# Ingest

## Purpose

Describes the `add` side of the [Pipeline](pipeline.md): how a reference becomes a stored source with candidates, and how `status` and `reextract` read and rework what is stored. Read this before adding a source adapter, changing how pages are fetched, or changing the commands' output.

## Commands

| Command | Use case | Does |
|---|---|---|
| `learn-german add <url\|file.txt>... [--from FILE] [--force]` | `AddSources` | Fetch or read each source, extract chunks, store both; one line per source, then a summary |
| `learn-german status [--top N]` | `ShowStatus` | Five most recent sources, pending and partial chunk counts, top N pending chunks (default 10) |
| `learn-german reextract` | `Reextract` | Run the extractors again over every stored text, without fetching |

`--from FILE` reads one reference per line; blank lines and lines starting with `#` are skipped, and relative paths resolve against the working directory ([0045](../decisions/0045-build-the-cli-with-create-app-and-stream-outcomes.md)).

## Source adapters

Each reference goes to the first adapter whose `can_handle(ref)` is true. `bootstrap.source_adapters` asks them in this order:

| Adapter | Handles | Reference stored | Title |
|---|---|---|---|
| `NewsUrlSource` | `http://` and `https://` URLs with a host | The URL as given | trafilatura's page title |
| `LocalFileSource` | Anything else ending in `.txt` (any case) | The absolute path | The file name without `.txt` |

A reference no adapter handles fails with a message naming what is accepted. Both live in `adapters/sources/` and raise `SourceFetchError`, an `ItemError`, when a source cannot be read.

### Text and hash

`normalise_text` is shared by both adapters ([0044](../decisions/0044-normalise-source-text-by-paragraph-before-hashing.md)): NFC, paragraphs split at blank lines, other whitespace collapsed to one space, paragraphs joined by one blank line. The content hash is the SHA-256 hex digest of that text, which is also what is stored and extracted.

### Local files

UTF-8, with or without a byte-order mark. Missing, unreadable, non-UTF-8 and empty files fail with a message that says what to do.

### News URLs

Following [0013](../decisions/0013-fetch-articles-politely-without-bypassing-paywalls.md) and [0043](../decisions/0043-check-robots-txt-per-site-and-redirect-and-require-150-words.md):

1. Read the site's `robots.txt` once per command (redirects followed). 200 is parsed for agent `learn-german`; 401 and 403 forbid everything; other 4xx allow everything; 5xx and network errors fail the source.
2. If robots.txt forbids the URL, fail without requesting it.
3. Request the URL with User-Agent `learn-german/<version>` and a 20-second timeout. Follow at most five redirects by hand, checking robots.txt again whenever a redirect leads to another site.
4. 401, 402, 403: paywall or login. 404, 410: wrong address. 429: slow down. Other non-2xx: try later. A content type that is neither HTML nor XML fails.
5. Extract the main text with trafilatura (no comments, no tables), one paragraph per line, drop a headline that repeats the title, normalise.
6. Fewer than 150 words: fail as a likely paywall teaser or non-article.

Every failure message that could be solved by saving the text by hand points to the `.txt` fallback.

## `add`

Per reference, each step in its own short unit of work ([0042](../decisions/0042-recognise-known-sources-before-fetching-and-refresh-them-in-place.md)):

1. Pick the adapter.
2. Without `--force`: if the reference as typed is stored, skip without fetching.
3. Fetch or read.
4. If the source's reference or content hash is stored, skip (without `--force`).
5. Extract with every extractor, outside any transaction, so the database is not locked while spaCy parses.
6. In one unit of work: count the chunk keys no stored source had, then store the source and its candidates; with `--force` and a stored match, overwrite that row in place and update its candidates by the 0017 rules below.

| Outcome | Meaning | Counts as failure |
|---|---|---|
| `added` | New source stored | no |
| `refreshed` | Known source fetched again with `--force` | no |
| `skipped` | Known by reference or text | no |
| `failed` | Could not be read or stored; nothing stored for it | yes |

An `ItemError` fails only its source. A `FatalError`, such as a missing spaCy model or a database error, stops the command; sources already processed stay stored.

Example output:

```
added      https://zeitung.example/radwege "Neue Radwege für Beispielstadt": 4 chunks (3 new), 5 occurrences
skipped    artikel.txt: already added (same address or same text); --force fetches it again
failed     https://zeitung.example/abo: https://zeitung.example/abo refused access (HTTP 402), probably a paywall or login. ...
3 sources: 1 added, 1 skipped, 1 failed.
Run `learn-german status` to see the pending chunks.
```

`chunks` counts distinct keys in the source, `new` the keys no earlier source had, `occurrences` the candidate rows.

## Candidate rules for `reextract` and `add --force`

`application/extraction.py` applies [0017](../decisions/0017-split-the-cli-into-add-and-sync.md) per source. An occurrence is identified by chunk key and sentence within the source.

| Case | Result |
|---|---|
| Stored and found again | Kept: same row, context updated |
| Found, not stored | Added |
| Stored, not found, chunk has no notes | Removed |
| Stored, not found, chunk has a note in `pushed_notes` | Kept as the record of those notes |

Status is per chunk key ([0025](../decisions/0025-track-note-progress-per-chunk-key.md)), so kept and added occurrences need no status of their own. `reextract` reads every stored source, extracts each outside a transaction, and applies the rules in one unit of work per source.

## `status`

Reads SQLite only. Pending chunks come from `CandidateRepository.pending_chunks()` and are ordered by `OccurrenceRanker`, the ranker `sync` uses, without asking Anki; a chunk Anki already has can therefore show as pending ([0033](../decisions/0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)). Partial chunks are marked with the note they still need.

## Exit codes

0 when everything worked, skipped sources included; 1 when at least one source failed; 2 for a fatal or usage error, printed as `Error: <message>` on stderr.

## Tests

| Layer | File | Covers |
|---|---|---|
| Unit | `tests/unit/ingest/` | `AddSources`, `Reextract` (the four rules as one parametrised test), `ShowStatus`, with `FakeSource`, `FakeExtractor` and in-memory SQLite |
| Unit | `tests/unit/sources/`, `tests/unit/cli/` | Normalisation and hashing; presenter edge cases |
| Integration | `tests/integration/sources/` | `NewsUrlSource` against `httpx2.MockTransport` (robots.txt disallow never requests the article, refusals, teaser, timeout, redirects, synthetic HTML); `LocalFileSource` on real files |
| Contract | `tests/contract/test_sources.py` | `FakeSource` and both adapters behave alike |
| End to end | `tests/e2e/test_cli_ingest.py` | `add`, `--from`, `--force`, `status`, `reextract`, exit codes, through `create_app(Overrides(...))` |
| NLP | `tests/nlp/test_cli_add.py` | `add` and `status` on the fixture article with the real extractor |

## Related

- [Pipeline](pipeline.md)
- [Code architecture](code-architecture.md)
- [NVV extraction](nvv-extraction.md)
- [Data model](../data/data-model.md)

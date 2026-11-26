---
title: Settle runtime dependencies up front, httpx2 and the spaCy model extra
summary: anthropic, httpx2 and spaCy 3.8 are added before the tracks; httpx2 replaces httpx as the SDK uses it; the spaCy model is an optional extra.
status: active
updated: 2026-11-26
---

# Settle runtime dependencies up front, httpx2 and the spaCy model extra

## Context

M2 needs spaCy, M5 the Anthropic SDK and an HTTP client to mock, M6 an HTTP client for AnkiConnect. If each track added its own, all of them would rewrite `uv.lock` and conflict ([0026](0026-run-m2-m4-m5-m6-as-parallel-tracks.md)). [0016](0016-use-standard-python-tooling.md) chose `httpx`, but the Anthropic SDK 2.x is built on `httpx2`, a separate package with the same API, and only accepts an `httpx2.Client` as its custom HTTP client. The roadmap left M2 to decide how the 500 MB spaCy model is installed.

## Decision

- Add `anthropic>=2.14`, `httpx2>=2.16` and `spacy>=3.8,<3.9` to the runtime dependencies in one change.
- **Use `httpx2`, not `httpx`,** for every HTTP call the tool makes: AnkiConnect (M6), news fetching (M3) and the mocked transport in tests (`httpx2.MockTransport`). This supersedes the `httpx` choice in 0016. One HTTP stack, and the SDK's client and ours are the same type.
- **The spaCy model is the optional extra `model`,** pinned by wheel URL to `de_core_news_lg-3.8.0`. Its version must match spaCy's minor version, so spaCy is capped at `<3.9` until both are bumped together. Users install `learn-german[model]`; developers run `uv sync --extra model`; only the CI `nlp` job installs it.
- import-linter forbids `anthropic`, `httpx2` and `spacy` in `domain`, `ports` and `application`.

## Alternatives considered

- **Keep `httpx` beside `httpx2`:** two near-identical HTTP stacks, and test helpers written for one do not work with the other.
- **Download the model with `spacy download` at first run:** needs network at run time and is not locked.
- **Model as a regular dependency:** every CI job and every install would download 500 MB.

## Consequences

- `httpx` still appears in `uv.lock` as a transitive dependency of other packages, but the code does not import it.
- A spaCy upgrade must bump the model URL in the same change, or `uv lock` fails to resolve.

## Related

- [0016 Use standard Python tooling](0016-use-standard-python-tooling.md)
- [Local setup](../development/setup.md)

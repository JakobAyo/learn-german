---
title: License the code under MIT
summary: The public repository is released under the MIT licence, the shortest permissive option.
status: active
updated: 2026-11-24
---

# License the code under MIT

## Context

The repository is public (see [0002](0002-build-a-single-user-python-cli-in-a-public-repo.md)). Without a licence, nobody may legally reuse the code. The requirements listed the licence as an open question.

## Decision

The code is released under the MIT licence, in a `LICENSE` file at the repository root.

## Alternatives considered

- Apache-2.0: rejected. Its explicit patent grant has no value for a personal learning tool, and the text and notice rules are longer.
- GPL-3.0: rejected. Copyleft adds obligations for reusers without protecting anything the owner cares about.

## Consequences

- Anything that is added to the repository must be compatible with MIT. This matters for word lists and other data files: check their licence before committing them (see [0009](0009-deduplicate-by-chunk-key-and-cap-new-notes-per-run.md)).
- The licence covers the code only. Mined text and generated cards never enter the repository.

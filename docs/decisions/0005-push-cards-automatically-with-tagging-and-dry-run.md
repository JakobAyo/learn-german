---
title: Push cards automatically, with tagging and dry run as safeguards
summary: There is no review step; generated notes go straight to Anki, each tagged with provider, model and run ID, and --dry-run previews a run.
status: active
updated: 2026-11-24
---

# Push cards automatically, with tagging and dry run as safeguards

## Context

The point of the tool is to save the owner from building cards by hand. A review step would bring part of that work back. But LLM output can be wrong, and a wrong model answer on a card trains the error.

## Decision

- No review or approval step. Generated notes are added to Anki directly.
- Every note is tagged with the LLM provider, the model and a run ID, so a bad batch can be found and deleted in Anki.
- A `--dry-run` flag runs the full pipeline and prints what would be added, without writing to Anki.
- No automatic self-check pass for now.

## Alternatives considered

- Always review before export: rejected, because it adds manual work the tool exists to remove.
- Review only the LLM-generated parts: rejected, because every v1 card has generated parts, so this equals full review.
- An LLM self-check pass: deferred. It doubles cost; revisit if the error rate turns out to be high.
- A report-a-bad-card feedback loop: deferred.

## Consequences

- Wrong cards will reach the deck. The owner fixes or deletes them while studying.
- The error rate of generated content should be measured once v1 runs. If it is high, add a self-check pass or a review step in a new record that supersedes this one.

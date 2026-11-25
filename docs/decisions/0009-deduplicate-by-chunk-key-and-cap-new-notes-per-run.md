---
title: Deduplicate by chunk key, rank candidates and cap new notes per run
summary: Chunks already in the deck are skipped by lemma key; a configurable cap limits new notes per run, ranked by occurrences in the learner's sources.
status: active
updated: 2026-11-24
---

# Deduplicate by chunk key, rank candidates and cap new notes per run

## Context

Cards are pushed automatically (see [0005](0005-push-cards-automatically-with-tagging-and-dry-run.md)), so nothing stops a run from flooding the deck or adding the same chunk twice. The cap also bounds LLM cost.

## Decision

- **Deduplication:** each chunk has a normalised lemma key (for example `entscheidung|treffen`), stored in a note field. A candidate whose key already exists in the tool's deck is skipped. Existing notes are not updated with new examples.
- **Cap:** the maximum number of new notes per run comes from a CLI flag, then an environment variable, then a default.
- **Ranking:** when candidates exceed the cap, rank by how often each chunk occurs across the learner's processed sources, counted from the local database, most frequent first. The ranker is an interface, so signals can be added or reweighted.
- Candidates beyond the cap stay pending in SQLite for later runs.

## Alternatives considered

- Adding a new example to the existing note: rejected, because notes would change under the learner over time.
- Allowing duplicates: rejected, because it wastes reviews.
- No cap: rejected, because an automatic run could add hundreds of notes and incur matching LLM cost.
- Ranking by an external frequency list: rejected for v1. Common German frequency lists count single words, not chunks, and some have licences that limit publishing in a public repo. Counting occurrences in the learner's own sources needs no outside data and reflects what the learner actually reads.
- Ranking by a match against a curated NVV list: rejected for v1. The light-verb whitelist already removes most false hits, and no suitable freely licensed list has been identified.

## Consequences

- The chunk key format is effectively permanent once notes exist. Changing it needs a migration of existing notes.
- Ranking is weak at first, when few sources have been processed and most chunks occur once. It improves as more material is fed in.
- An external frequency list or curated NVV list can be added later as a ranker signal. Check its licence before committing it; otherwise download it at setup time.

Refined later: the key format is fixed in [0011](0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md); [0012](0012-make-both-cards-practise-the-chunk.md) makes the cap count chunks and checks duplicates per note type; [0015](0015-set-v1-run-defaults.md) sets the default cap to 10 chunks.

---
title: Guard extraction quality with a golden-corpus baseline
summary: Hand-written sentences with expected keys are scored for micro-averaged precision and recall; the nlp test fails below the baseline stored next to the corpus.
status: active
updated: 2026-11-26
---

# Guard extraction quality with a golden-corpus baseline

## Context

The [Roadmap](../product/roadmap.md) M2 asks for a golden corpus whose precision and recall cannot quietly drop, so a change to the light-verb list or the matcher cannot make extraction worse. It left open the file format, how to score, where the baseline lives and when it may change.

## Decision

- **Corpus:** `tests/data/nlp/golden_corpus.tsv`, one hand-written synthetic sentence per line (0002), a tab, then the expected keys separated by spaces, or `-` for none. Expected keys say what a careful reader would extract, not what the extractor does today, so known misses and false positives stay visible. It includes sentences without an NVV, so false positives count.
- **Score:** each sentence is extracted alone; expected and found keys are compared as sets per sentence and counted over the whole corpus (micro-averaged): precision = hits / found, recall = hits / expected.
- **Baseline:** `tests/data/nlp/golden_baseline.json` holds precision and recall rounded down to three decimals, with the counts, date and model version. The `nlp` test fails if either value is below the baseline and prints every sentence that differs.
- **Changing the baseline:** raise it in the same change that improves extraction. Lower it only when the model is upgraded or sentences are added to the corpus, and say why in the commit message; never to let a matcher or word-list change through.
- **Honest numbers:** the matcher rules were tuned on the first 58 sentences. The last 12 were written afterwards and were not tuned against, and they are scored together with the rest.

The first baseline, with `de_core_news_lg` 3.8.0, is precision 0.888 (48 of 54 found keys right) and recall 0.923 (48 of 52 expected keys found).

## Alternatives considered

- **Exact-match tests per sentence:** every known miss would be a failing or `xfail` test; a change that fixes one sentence and breaks another would be hard to judge.
- **A tolerance below the baseline:** lets small losses add up unnoticed; the corpus is small and the model deterministic, so the numbers do not jitter.
- **Real news sentences:** better coverage, but the repository is public and must not contain copied text (R28).

## Consequences

- The corpus is small and partly tuned against, so the baseline guards against regressions; it is not an estimate of quality on real articles.
- Adding sentences can lower the score without any code change; record a new baseline in the same commit.

## Related

- [0029 Match NVVs in ranked tiers](0029-match-nvvs-in-ranked-tiers-without-a-noun-lexicon.md)
- [Testing strategy](../development/testing-strategy.md)
- [NVV extraction](../system-design/nvv-extraction.md)

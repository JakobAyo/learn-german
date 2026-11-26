"""Precision and recall on the golden corpus must not drop below the recorded baseline (0031)."""

import pytest

from learn_german.adapters.nlp import NvvExtractor
from tests.nlp.golden import load_baseline, load_corpus, score

pytestmark = pytest.mark.nlp


def test_nvv_extractor_keeps_golden_corpus_baseline(nvv_extractor: NvvExtractor) -> None:
    corpus = load_corpus()
    baseline = load_baseline()

    results = [
        (golden.expected, frozenset(c.key.value for c in nvv_extractor.extract(golden.sentence)))
        for golden in corpus
    ]
    result = score(results)

    differences = "\n".join(
        f"  {golden.sentence}  expected {sorted(expected)}, found {sorted(found)}"
        for golden, (expected, found) in zip(corpus, results, strict=True)
        if expected != found
    )
    summary = (
        f"precision {result.precision:.3f} (baseline {baseline.precision}), "
        f"recall {result.recall:.3f} (baseline {baseline.recall})\n{differences}"
    )
    assert result.precision >= baseline.precision, summary
    assert result.recall >= baseline.recall, summary

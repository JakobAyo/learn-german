"""The golden corpus file and its scoring, checked without the model (0031)."""

import pytest

from learn_german.domain.models import ChunkKey
from tests.nlp.golden import GoldenSentence, Score, load_baseline, load_corpus, read_corpus, score


def test_golden_corpus_has_about_fifty_sentences_without_duplicates() -> None:
    sentences = [golden.sentence for golden in load_corpus()]

    assert len(sentences) >= 50
    assert len(sentences) == len(set(sentences))


def test_golden_corpus_keys_follow_0011() -> None:
    for golden in load_corpus():
        for key in golden.expected:
            ChunkKey(key)


def test_golden_corpus_holds_sentences_without_nvv() -> None:
    assert any(not golden.expected for golden in load_corpus())


def test_golden_baseline_is_a_pair_of_ratios() -> None:
    baseline = load_baseline()

    assert 0 < baseline.precision <= 1
    assert 0 < baseline.recall <= 1


def test_read_corpus_parses_keys_and_none() -> None:
    content = "# comment\n\nA.\tfrage|stellen rolle|spielen\nB.\t-\n"

    assert read_corpus(content) == [
        GoldenSentence("A.", frozenset({"frage|stellen", "rolle|spielen"})),
        GoldenSentence("B.", frozenset()),
    ]


def test_score_counts_hits_misses_and_extras() -> None:
    result = score(
        [
            (frozenset({"a|b", "c|d"}), frozenset({"a|b"})),
            (frozenset(), frozenset({"e|f"})),
            (frozenset({"g|h"}), frozenset({"g|h"})),
        ]
    )

    assert result == Score(true_positives=2, false_positives=1, false_negatives=1)
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(2 / 3)


def test_score_of_nothing_found_and_nothing_expected_is_perfect() -> None:
    result = score([(frozenset(), frozenset())])

    assert (result.precision, result.recall) == (1.0, 1.0)

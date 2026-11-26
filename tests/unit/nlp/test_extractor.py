"""NvvExtractor with a stub parser: candidates, order and context window (R10)."""

import pytest

from learn_german.adapters.nlp.extractor import NvvExtractor, context_window
from learn_german.adapters.nlp.tokens import ParsedSentence
from learn_german.domain.models import Candidate, ChunkKey, ChunkKind
from learn_german.ports import ChunkExtractor
from tests.unit.nlp.builders import LEXICON, parsed

DECISION = parsed(
    "Der der DET ART nk 1",
    "Rat Rat NOUN NN sb 2",
    "traf treffen VERB VVFIN ROOT 2",
    "eine ein DET ART nk 4",
    "Entscheidung Entscheidung NOUN NN oa 2",
    ". -- PUNCT $. punct 2",
)
ROLE = parsed(
    "Geld Geld NOUN NN sb 1",
    "spielt spielen VERB VVFIN ROOT 1",
    "keine kein DET PIAT nk 3",
    "Rolle Rolle NOUN NN oa 1",
    ". -- PUNCT $. punct 1",
)
RAIN = parsed("Es es PRON PPER sb 1", "regnet regnen VERB VVFIN ROOT 1", ". -- PUNCT $. punct 1")


class StubParser:
    def __init__(self, *sentences: ParsedSentence) -> None:
        self.sentences = list(sentences)
        self.texts: list[str] = []

    def parse(self, text: str) -> list[ParsedSentence]:
        self.texts.append(text)
        return self.sentences


def test_nvv_extractor_satisfies_the_chunk_extractor_port() -> None:
    extractor: ChunkExtractor = NvvExtractor(StubParser(), LEXICON)

    assert extractor.kind is ChunkKind.NVV


def test_nvv_extractor_returns_candidates_in_text_order_with_context() -> None:
    parser = StubParser(RAIN, DECISION, RAIN, ROLE)
    extractor = NvvExtractor(parser, LEXICON)

    candidates = extractor.extract("the text")

    assert parser.texts == ["the text"]
    assert candidates == [
        Candidate(
            ChunkKey("entscheidung|treffen"),
            ChunkKind.NVV,
            DECISION.text,
            f"{RAIN.text} {DECISION.text} {RAIN.text}",
        ),
        Candidate(ChunkKey("rolle|spielen"), ChunkKind.NVV, ROLE.text, f"{RAIN.text} {ROLE.text}"),
    ]


def test_nvv_extractor_returns_a_chunk_once_per_sentence() -> None:
    twice = parsed(
        "Er er PRON PPER sb 1",
        "spielte spielen VERB VVFIN ROOT 1",
        "keine kein DET PIAT nk 3",
        "Rolle Rolle NOUN NN oa 1",
        "und und CCONJ KON cd 1",
        "spielt spielen VERB VVFIN cj 4",
        "keine kein DET PIAT nk 7",
        "Rolle Rolle NOUN NN oa 5",
    )

    candidates = NvvExtractor(StubParser(twice), LEXICON).extract("x")

    assert [c.key for c in candidates] == [ChunkKey("rolle|spielen")]


def test_nvv_extractor_finds_nothing_in_text_without_nvv() -> None:
    assert NvvExtractor(StubParser(RAIN), LEXICON).extract("x") == []


def test_nvv_extractor_default_builds_without_loading_the_model() -> None:
    # Building is cheap; the spaCy model only loads on the first extract.
    assert NvvExtractor.default().kind is ChunkKind.NVV


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        pytest.param(0, "A. B.", id="first"),
        pytest.param(1, "A. B. C.", id="middle"),
        pytest.param(2, "B. C.", id="last"),
    ],
)
def test_context_window_keeps_one_sentence_each_side(index: int, expected: str) -> None:
    sentences = [ParsedSentence(text, ()) for text in ("A.", "B.", "C.")]

    assert context_window(sentences, index) == expected


def test_context_window_of_a_single_sentence_is_the_sentence() -> None:
    assert context_window([ParsedSentence("A.", ())], 0) == "A."

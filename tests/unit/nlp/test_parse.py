"""The spaCy boundary, tested with blank pipelines and hand-made Docs instead of the model."""

import pytest
import spacy
from spacy.language import Language
from spacy.tokens import Doc

from learn_german.adapters.nlp.parse import MODEL_NAME, SpacyParser, doc_sentences, paragraphs
from learn_german.adapters.nlp.tokens import TokenView
from learn_german.domain.errors import NlpModelMissingError


def _blank_pipeline(name: str) -> Language:
    nlp = spacy.blank("de")
    nlp.add_pipe("sentencizer")
    return nlp


class CountingLoader:
    def __init__(self) -> None:
        self.names: list[str] = []

    def __call__(self, name: str) -> Language:
        self.names.append(name)
        return _blank_pipeline(name)


def test_doc_sentences_converts_tokens_with_sentence_relative_heads() -> None:
    nlp = spacy.blank("de")
    doc = Doc(
        nlp.vocab,
        words=["Es", "regnet", ".", "Er", "traf", "eine", "Entscheidung", "."],
        spaces=[True, False, True, True, True, True, False, False],
        heads=[1, 1, 1, 4, 4, 6, 4, 4],
        deps=["sb", "ROOT", "punct", "sb", "ROOT", "nk", "oa", "punct"],
        pos=["PRON", "VERB", "PUNCT", "PRON", "VERB", "DET", "NOUN", "PUNCT"],
        tags=["PPER", "VVFIN", "$.", "PPER", "VVFIN", "ART", "NN", "$."],
        lemmas=["es", "regnen", "--", "er", "treffen", "ein", "Entscheidung", "--"],
        morphs=["", "", "", "", "", "", "Case=Acc|Number=Sing", ""],
        sent_starts=[True, False, False, True, False, False, False, False],
    )

    sentences = doc_sentences(doc)

    assert [s.text for s in sentences] == ["Es regnet.", "Er traf eine Entscheidung."]
    assert sentences[1].tokens[3] == TokenView(
        index=3,
        text="Entscheidung",
        lemma="Entscheidung",
        pos="NOUN",
        tag="NN",
        dep="oa",
        head=1,
        morph="Case=Acc|Number=Sing",
    )
    assert sentences[1].tokens[1].head == 1


def test_paragraphs_split_at_blank_lines_and_collapse_whitespace() -> None:
    text = "Erste Zeile\nzweite Zeile.\n\n  \n\nNeuer   Absatz.\n"

    assert paragraphs(text) == ["Erste Zeile zweite Zeile.", "Neuer Absatz."]


def test_paragraphs_of_blank_text_is_empty() -> None:
    assert paragraphs(" \n\n \t") == []


def test_spacy_parser_loads_the_model_once_and_only_when_parsing() -> None:
    loader = CountingLoader()
    parser = SpacyParser(loader=loader)

    assert loader.names == []
    parser.parse("Es regnet.")
    parser.parse("Es schneit.")

    assert loader.names == [MODEL_NAME]


def test_spacy_parser_returns_sentences_across_paragraphs_in_order() -> None:
    parser = SpacyParser(loader=_blank_pipeline)

    sentences = parser.parse("Es regnet. Es schneit.\n\nDie Sonne scheint.")

    assert [s.text for s in sentences] == ["Es regnet.", "Es schneit.", "Die Sonne scheint."]


def test_spacy_parser_raises_model_missing_when_the_model_is_not_installed() -> None:
    def missing(name: str) -> Language:
        raise OSError(f"[E050] Can't find model '{name}'.")

    parser = SpacyParser(loader=missing)

    with pytest.raises(NlpModelMissingError, match="uv sync --extra model"):
        parser.parse("Es regnet.")

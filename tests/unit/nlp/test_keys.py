import pytest

from learn_german.adapters.nlp.keys import (
    CONTRACTIONS,
    NvvMatch,
    build_key,
    preposition_lemma,
    verb_infinitive,
)
from learn_german.adapters.nlp.tokens import TokenView
from learn_german.domain.models import ChunkKey
from tests.unit.nlp.builders import LEXICON, nvv, token

VARIANTS = LEXICON.spelling_variants

# Every row of the 0011 table, built from the tokens the matcher would hand over.
TABLE = [
    pytest.param(
        nvv("Verfügung Verfügung NOUN NN nk 0", "stellen stellen VERB VVINF ROOT 0",
            preposition="zur zu ADP APPRART cvc 0"),
        "verfügung|zu|stellen", id="zur Verfügung stellen",
    ),
    pytest.param(
        nvv("Verfügung Verfügung NOUN NN nk 0", "stehen stehen VERB VVINF ROOT 0",
            preposition="zur zu ADP APPRART cvc 0"),
        "verfügung|zu|stehen", id="zur Verfügung stehen",
    ),
    pytest.param(
        nvv("Frage Frage NOUN NN nk 0", "stellen stellen VERB VVINF ROOT 0",
            preposition="in in ADP APPR cvc 0"),
        "frage|in|stellen", id="in Frage stellen",
    ),
    pytest.param(
        nvv("Frage Frage NOUN NN oa 0", "stellen stellen VERB VVINF ROOT 0"),
        "frage|stellen", id="eine Frage stellen",
    ),
    pytest.param(
        nvv("Rolle Rolle NOUN NN oa 0", "spielen spielen VERB VVINF ROOT 0"),
        "rolle|spielen", id="keine Rolle spielen",
    ),
    pytest.param(
        nvv("Acht Acht NUM CARD nk 0", "nehmen nehmen VERB VVINF ROOT 0",
            preposition="in in ADP APPR mo 0", reflexive=True),
        "acht|in|sich|nehmen", id="sich in Acht nehmen",
    ),
    pytest.param(
        nvv("Entscheidung Entscheidung NOUN NN oa 0", "traf treffen VERB VVFIN ROOT 0"),
        "entscheidung|treffen", id="traf eine Entscheidung",
    ),
    pytest.param(
        nvv("infrage infrag ADJ ADJD mo 0", "stellen stellen VERB VVINF ROOT 0"),
        "frage|in|stellen", id="infrage stellen",
    ),
]  # fmt: skip


@pytest.mark.parametrize(("match", "expected"), TABLE)
def test_build_key_follows_0011_table(match: NvvMatch, expected: str) -> None:
    assert build_key(match, VARIANTS) == ChunkKey(expected)


def test_build_key_maps_a_capitalised_spelling_variant() -> None:
    match = nvv("Infrage Infrage NOUN NN mo 0", "stellen stellen VERB VVINF ROOT 0")

    assert build_key(match, VARIANTS) == ChunkKey("frage|in|stellen")


def test_build_key_puts_the_verbs_own_prefix_in_front() -> None:
    match = nvv("Kontakt Kontakt NOUN NN oa 0", "nahm nehmen VERB VVFIN ROOT 0",
                particle="auf auf ADP PTKVZ svp 0")  # fmt: skip

    assert build_key(match, VARIANTS) == ChunkKey("kontakt|aufnehmen")


def test_build_key_falls_back_to_the_text_without_a_lemma() -> None:
    noun = TokenView(0, "Abschied", "", "NOUN", "NN", "oa", 0)
    match = NvvMatch(token("nehmen nehmen VERB VVINF ROOT 0"), noun)

    assert build_key(match, VARIANTS) == ChunkKey("abschied|nehmen")


@pytest.mark.parametrize(
    "noun",
    [
        pytest.param("COVID-19 COVID-19 NOUN NN oa 0", id="digits"),
        pytest.param("Café Café NOUN NN oa 0", id="accent"),
    ],
)
def test_build_key_skips_lemmas_a_chunk_key_rejects(noun: str) -> None:
    match = nvv(noun, "nehmen nehmen VERB VVINF ROOT 0")

    assert build_key(match, VARIANTS) is None


@pytest.mark.parametrize(("contraction", "preposition"), sorted(CONTRACTIONS.items()))
def test_preposition_lemma_expands_contraction(contraction: str, preposition: str) -> None:
    assert preposition_lemma(token(f"{contraction.title()} x ADP APPRART cvc 0")) == preposition


def test_preposition_lemma_lowercases_a_plain_preposition() -> None:
    assert preposition_lemma(token("In in ADP APPR mo 0")) == "in"


@pytest.mark.parametrize(
    ("verb", "particle", "expected"),
    [
        pytest.param("stellte stellen VERB VVFIN ROOT 0", None, "stellen", id="no-particle"),
        pytest.param("nahm nehmen VERB VVFIN ROOT 0", "auf auf ADP PTKVZ svp 0", "aufnehmen",
                     id="separated-particle"),
        pytest.param("aufgenommen aufnehmen VERB VVPP oc 0", "auf auf ADP PTKVZ svp 0",
                     "aufnehmen", id="prefix-already-in-lemma"),
    ],
)  # fmt: skip
def test_verb_infinitive_attaches_the_separable_prefix(
    verb: str, particle: str | None, expected: str
) -> None:
    assert verb_infinitive(token(verb), None if particle is None else token(particle)) == expected

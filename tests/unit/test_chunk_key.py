import pytest

from learn_german.domain.models import ChunkKey

# Every row of the 0011 table, plus a reflexive without preposition and a hyphenated noun.
VALID = [
    ("verfügung|zu|stellen", "verfügung", "zu", False, "stellen"),
    ("verfügung|zu|stehen", "verfügung", "zu", False, "stehen"),
    ("frage|in|stellen", "frage", "in", False, "stellen"),
    ("frage|stellen", "frage", None, False, "stellen"),
    ("rolle|spielen", "rolle", None, False, "spielen"),
    ("acht|in|sich|nehmen", "acht", "in", True, "nehmen"),
    ("entscheidung|treffen", "entscheidung", None, False, "treffen"),
    ("mühe|sich|geben", "mühe", None, True, "geben"),
    ("e-mail|schreiben", "e-mail", None, False, "schreiben"),
]
VALID_IDS = [row[0] for row in VALID]


@pytest.mark.parametrize(
    ("value", "noun", "preposition", "reflexive", "verb"), VALID, ids=VALID_IDS
)
def test_chunk_key_accepts_0011_format(
    value: str, noun: str, preposition: str | None, reflexive: bool, verb: str
) -> None:
    key = ChunkKey(value)

    assert (key.noun, key.preposition, key.reflexive, key.verb) == (
        noun,
        preposition,
        reflexive,
        verb,
    )


@pytest.mark.parametrize(
    ("value", "noun", "preposition", "reflexive", "verb"), VALID, ids=VALID_IDS
)
def test_chunk_key_from_parts_builds_the_same_key(
    value: str, noun: str, preposition: str | None, reflexive: bool, verb: str
) -> None:
    key = ChunkKey.from_parts(noun, verb, preposition=preposition, reflexive=reflexive)

    assert key == ChunkKey(value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("entscheidung", id="noun-only"),
        pytest.param("Entscheidung|treffen", id="uppercase"),
        pytest.param("rolle | spielen", id="spaces"),
        pytest.param("rolle||spielen", id="empty-part"),
        pytest.param("rolle|spielen|", id="trailing-separator"),
        pytest.param("verfügung|zur|stellen", id="contraction-zur"),
        pytest.param("frage|im|stehen", id="contraction-im"),
        pytest.param("entscheidung|eine|treffen", id="article"),
        pytest.param("rolle|keine|spielen", id="negation"),
        pytest.param("sich|nehmen", id="sich-as-noun"),
        pytest.param("acht|nehmen|sich", id="sich-as-verb"),
        pytest.param("acht|sich|in|nehmen", id="sich-before-preposition"),
        pytest.param("frage|in|zu|stellen", id="two-prepositions"),
        pytest.param("frage|in|sich|sich|stellen", id="sich-twice"),
        pytest.param("frage|stellen2", id="digit"),
        pytest.param("-frage|stellen", id="leading-hyphen"),
    ],
)
def test_chunk_key_rejects_values_outside_0011(value: str) -> None:
    with pytest.raises(ValueError, match="chunk key"):
        ChunkKey(value)


def test_chunk_key_is_usable_as_dict_key() -> None:
    counts = {ChunkKey("rolle|spielen"): 1}

    assert counts[ChunkKey("rolle|spielen")] == 1


def test_chunk_key_str_is_its_value() -> None:
    assert str(ChunkKey("frage|in|stellen")) == "frage|in|stellen"

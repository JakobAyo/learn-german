from importlib.resources import files

import pytest

from learn_german.adapters.nlp.lexicon import (
    LIGHT_VERBS_FILE,
    SPELLING_VARIANTS_FILE,
    Lexicon,
    SpellingVariant,
    read_light_verbs,
    read_spelling_variants,
)
from learn_german.domain.models import ChunkKey

DATA = files("learn_german.adapters.nlp").joinpath("data")
# DIN 5007-1: umlauts sort as their base letter, ß as ss. The data file headers say so.
_GERMAN_SORT = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss"})


def _entries(name: str) -> list[str]:
    lines = DATA.joinpath(name).read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def _first_columns(name: str) -> list[str]:
    return [line.split("\t")[0] for line in _entries(name)]


@pytest.mark.parametrize("name", [LIGHT_VERBS_FILE, SPELLING_VARIANTS_FILE])
def test_data_file_is_lowercase(name: str) -> None:
    assert all(line == line.lower() for line in _entries(name))


@pytest.mark.parametrize("name", [LIGHT_VERBS_FILE, SPELLING_VARIANTS_FILE])
def test_data_file_has_no_duplicates(name: str) -> None:
    words = _first_columns(name)

    assert len(words) == len(set(words))


@pytest.mark.parametrize("name", [LIGHT_VERBS_FILE, SPELLING_VARIANTS_FILE])
def test_data_file_is_sorted(name: str) -> None:
    words = _first_columns(name)

    assert words == sorted(words, key=lambda word: (word.translate(_GERMAN_SORT), word))


def test_light_verbs_are_single_words() -> None:
    assert all(verb.isalpha() for verb in _entries(LIGHT_VERBS_FILE))


def test_spelling_variants_give_valid_key_parts() -> None:
    lexicon = Lexicon.load()

    for variant in lexicon.spelling_variants.values():
        ChunkKey.from_parts(variant.noun, "stellen", preposition=variant.preposition)


def test_lexicon_load_reads_both_files() -> None:
    lexicon = Lexicon.load()

    assert "stellen" in lexicon.light_verbs
    assert lexicon.spelling_variants["infrage"] == SpellingVariant("frage", "in")


def test_read_light_verbs_skips_comments_and_blank_lines() -> None:
    assert read_light_verbs("# header\n\nstellen\n  nehmen  \n") == {"stellen", "nehmen"}


def test_read_spelling_variants_parses_three_columns() -> None:
    variants = read_spelling_variants("# header\ninfrage\tfrage\tin\n")

    assert dict(variants) == {"infrage": SpellingVariant("frage", "in")}


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("infrage\tfrage", id="two-columns"),
        pytest.param("infrage\tfrage\tin\textra", id="four-columns"),
        pytest.param("infrage\t\tin", id="empty-column"),
        pytest.param("infrage frage in", id="spaces"),
    ],
)
def test_read_spelling_variants_rejects_malformed_line(line: str) -> None:
    with pytest.raises(ValueError, match="three tab-separated columns"):
        read_spelling_variants(line)

"""Sanity checks on card content beyond the schema (0036)."""

import pytest

from learn_german.application.generation import CheckedProvider, check_card
from learn_german.application.generation.checks import count_words, problems, word_range
from learn_german.domain.errors import GenerationError
from learn_german.domain.models import CardContent, CardRequest, ChunkKey
from learn_german.ports import LLMProvider
from tests.fakes.llm import FakeProvider
from tests.unit.generation.builders import CONTENT, REQUEST, content, request

APPLICATION = ChunkKey("antrag|stellen")
QUESTION = ChunkKey("frage|in|stellen")
SHORT_SOURCE = "Der Rat traf gestern eine Entscheidung."  # 6 words

TWENTY_SIX = (
    "Der Stadtrat der Stadt hat am Montagabend nach einer sehr langen und zum Teil heftigen "
    "Sitzung endlich eine Entscheidung über den Bau der neuen Brücke getroffen."
)


@pytest.mark.parametrize(
    ("req", "card", "expected"),
    [
        pytest.param(REQUEST, CONTENT, [], id="valid"),
        pytest.param(
            request(key=APPLICATION),
            content(
                citation_form="einen Antrag stellen",
                shortened_sentence=(
                    "Die Fraktion hat im Ausschuss mehrere Anträge zur Finanzierung der Schulen "
                    "gestellt."
                ),
            ),
            [],
            id="umlaut-plural-matches-noun",
        ),
        pytest.param(
            request(key=QUESTION),
            content(
                citation_form="infrage stellen",
                shortened_sentence=(
                    "Die Opposition hat den Plan der Regierung zum Bau der Brücke infrage gestellt."
                ),
            ),
            [],
            id="one-word-spelling-holds-noun",
        ),
        pytest.param(
            REQUEST,
            content(
                shortened_sentence=(
                    "Der Stadtrat hat endlich über den Bau der neuen Brücke abgestimmt und beraten."
                )
            ),
            ["does not contain the noun 'entscheidung'"],
            id="noun-missing",
        ),
        pytest.param(
            REQUEST,
            content(shortened_sentence="Der Rat traf eine Entscheidung."),
            ["has 5 words, expected 8 to 25"],
            id="too-short",
        ),
        pytest.param(
            REQUEST,
            content(shortened_sentence=TWENTY_SIX),
            ["has 26 words, expected 8 to 25"],
            id="too-long",
        ),
        pytest.param(
            request(sentence=SHORT_SOURCE),
            content(shortened_sentence=SHORT_SOURCE),
            [],
            id="short-source-kept",
        ),
        pytest.param(
            request(sentence=SHORT_SOURCE),
            content(shortened_sentence="Der Rat traf eine Entscheidung."),
            [],
            id="short-source-shortened",
        ),
        pytest.param(
            request(sentence=SHORT_SOURCE),
            content(shortened_sentence="Der Rat der Stadt traf gestern eine Entscheidung."),
            ["has 8 words, expected 1 to 6"],
            id="short-source-made-longer",
        ),
        pytest.param(
            REQUEST,
            content(citation_form="einen Beschluss treffen"),
            ["lacks the noun 'entscheidung'"],
            id="citation-without-noun",
        ),
        pytest.param(
            REQUEST,
            content(citation_form="eine Entscheidung fällen"),
            ["lacks the verb 'treffen'"],
            id="citation-without-verb",
        ),
        pytest.param(
            REQUEST,
            content(meaning="eine Entscheidung treffen = entscheiden\nsich festlegen"),
            ["meaning is longer than one line"],
            id="meaning-two-lines",
        ),
        pytest.param(
            REQUEST,
            content(citation_form="etwas tun", meaning="tun\nmachen"),
            ["lacks the noun", "lacks the verb", "meaning is longer than one line"],
            id="several-problems",
        ),
    ],
)
def test_problems_lists_each_failed_check(
    req: CardRequest, card: CardContent, expected: list[str]
) -> None:
    found = problems(req, card)

    assert len(found) == len(expected)
    for message, fragment in zip(found, expected, strict=True):
        assert fragment in message


@pytest.mark.parametrize(
    ("source_words", "bounds"),
    [
        pytest.param(3, (1, 3), id="three"),
        pytest.param(9, (1, 9), id="nine"),
        pytest.param(10, (8, 25), id="ten"),
        pytest.param(40, (8, 25), id="forty"),
    ],
)
def test_word_range_lets_short_sources_stay_short(
    source_words: int, bounds: tuple[int, int]
) -> None:
    assert word_range(source_words) == bounds


def test_count_words_ignores_dashes() -> None:
    assert count_words("Der Rat \u2013 so heißt es \u2013 traf 2026 eine Entscheidung.") == 9


def test_check_card_returns_valid_content_unchanged() -> None:
    assert check_card(REQUEST, CONTENT) is CONTENT


def test_check_card_raises_generation_error_with_every_problem() -> None:
    with pytest.raises(GenerationError, match=r"lacks the noun.*longer than one line"):
        check_card(REQUEST, content(citation_form="treffen", meaning="a\nb"))


def test_checked_provider_passes_identity_through() -> None:
    provider: LLMProvider = CheckedProvider(FakeProvider("p", "m", "v9"))

    assert (provider.name, provider.model, provider.prompt_version) == ("p", "m", "v9")


def test_checked_provider_returns_content_that_passes() -> None:
    fake = FakeProvider()
    fake.responses[REQUEST.key] = CONTENT

    assert CheckedProvider(fake).generate(REQUEST) == CONTENT


def test_checked_provider_rejects_content_that_fails() -> None:
    fake = FakeProvider()
    fake.responses[REQUEST.key] = content(meaning="a\nb")

    with pytest.raises(GenerationError):
        CheckedProvider(fake).generate(REQUEST)

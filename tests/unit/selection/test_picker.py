"""ShortestSentencePicker: shortest sentence of at least ten words, newest on ties (0032)."""

import pytest

from learn_german.application.selection import ShortestSentencePicker
from learn_german.application.selection.picker import MIN_WORDS, count_words
from learn_german.ports import OccurrencePicker
from tests.unit.selection.builders import occurrence

FIVE = "Der Rat traf eine Entscheidung."
SEVEN = "Am Montag traf der Rat eine Entscheidung."
TEN = "Nach langer Diskussion traf der Rat am Montag eine Entscheidung."
TEN_LATER = "Der Rat der Stadt traf gestern Abend eine wichtige Entscheidung."
FOURTEEN = (
    "Nach langer und teilweise heftiger Diskussion traf der Rat am Montag endlich "
    "eine Entscheidung."
)

PICKER: OccurrencePicker = ShortestSentencePicker()


@pytest.mark.parametrize(
    ("sentence", "words"),
    [
        pytest.param(FIVE, 5, id="five"),
        pytest.param(SEVEN, 7, id="seven"),
        pytest.param(TEN, 10, id="ten"),
        pytest.param(TEN_LATER, 10, id="ten-later"),
        pytest.param(FOURTEEN, 14, id="fourteen"),
        pytest.param(
            "Der Rat \u2013 so heißt es \u2013 traf 2026 eine Entscheidung.", 9, id="dash-number"
        ),
        pytest.param("  ", 0, id="blank"),
    ],
)
def test_count_words_counts_tokens_with_a_letter_or_digit(sentence: str, words: int) -> None:
    assert count_words(sentence) == words


def test_default_minimum_is_ten_words() -> None:
    assert MIN_WORDS == 10


@pytest.mark.parametrize(
    ("sentences", "picked"),
    [
        pytest.param([SEVEN], SEVEN, id="only-one"),
        pytest.param([FOURTEEN, TEN, FIVE], TEN, id="shortest-long-enough"),
        pytest.param([FIVE, FOURTEEN, SEVEN], FOURTEEN, id="long-enough-beats-shorter"),
        pytest.param([SEVEN, FIVE], SEVEN, id="all-too-short-takes-longest"),
        pytest.param([TEN, TEN_LATER, FOURTEEN], TEN_LATER, id="tie-takes-newest"),
        pytest.param([SEVEN, FIVE, SEVEN + " "], SEVEN + " ", id="too-short-tie-takes-newest"),
    ],
)
def test_picker_chooses(sentences: list[str], picked: str) -> None:
    occurrences = [occurrence(sentence) for sentence in sentences]

    assert PICKER.pick(occurrences).sentence == picked


def test_picker_minimum_is_configurable() -> None:
    picker = ShortestSentencePicker(min_words=6)

    assert picker.pick([occurrence(FIVE), occurrence(TEN), occurrence(SEVEN)]).sentence == SEVEN


def test_picker_returns_the_occurrence_with_its_context() -> None:
    chosen = occurrence(TEN, context="Es war spät. " + TEN)

    assert PICKER.pick([occurrence(FIVE), chosen]) is chosen


def test_picker_rejects_no_occurrences() -> None:
    with pytest.raises(ValueError, match="empty"):
        PICKER.pick([])


def test_picker_rejects_a_minimum_below_one() -> None:
    with pytest.raises(ValueError, match="1 or more"):
        ShortestSentencePicker(min_words=0)

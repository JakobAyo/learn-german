"""`ShortestSentencePicker`: the v1 `OccurrencePicker` (0032)."""

from collections.abc import Sequence

from learn_german.domain.models import Candidate

MIN_WORDS = 10
"""Fewest words a source sentence should have (0032).

The low end of the shortened sentence in 0012, so the LLM never has to make a sentence longer.
"""


def count_words(sentence: str) -> int:
    """Whitespace-separated tokens with at least one letter or digit; a lone dash is no word."""
    return sum(1 for token in sentence.split() if any(char.isalnum() for char in token))


class ShortestSentencePicker:
    """Picks the shortest sentence with at least `min_words` words (0032).

    If every sentence is shorter than that, it picks the longest one. Ties go to the most
    recent occurrence, which is the last one given, since occurrences come oldest first.
    Raises ValueError if `min_words` is below 1.
    """

    def __init__(self, min_words: int = MIN_WORDS) -> None:
        if min_words < 1:
            raise ValueError(f"min_words must be 1 or more, got {min_words}")
        self._min_words = min_words

    def pick(self, occurrences: Sequence[Candidate]) -> Candidate:
        """Raises ValueError if there are no occurrences."""
        if not occurrences:
            raise ValueError("cannot pick an occurrence from an empty list")
        # min() keeps the first of equal items, so walking newest first gives recency on ties.
        return min(reversed(occurrences), key=self._preference)

    def _preference(self, occurrence: Candidate) -> tuple[bool, int]:
        words = count_words(occurrence.sentence)
        too_short = words < self._min_words
        return (too_short, -words if too_short else words)

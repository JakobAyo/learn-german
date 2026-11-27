"""Cheap sanity checks on card content, beyond what the output schema can say (0036).

They are the first guard for the quality question in 0005: they catch output that is clearly
wrong for the chunk, not output that is subtly wrong. A failed check is a `GenerationError`,
so the chunk stays pending and the next run asks again (0014).
"""

from learn_german.domain.errors import GenerationError
from learn_german.domain.models import CardContent, CardRequest
from learn_german.ports import LLMProvider

SOURCE_MIN_WORDS = 10
"""The picker's minimum (0032). A source shorter than this had no longer alternative."""

MIN_WORDS = 8
"""Fewest words a shortened sentence may have. The prompt asks for 10 to 20 (0012)."""

MAX_WORDS = 25
"""Most words a shortened sentence may have."""

_FOLD = str.maketrans({"ä": "a", "ö": "o", "ü": "u"})


def count_words(sentence: str) -> int:
    """Whitespace-separated tokens with at least one letter or digit, as the picker counts."""
    return sum(1 for token in sentence.split() if any(char.isalnum() for char in token))


def word_range(source_words: int) -> tuple[int, int]:
    """Inclusive bounds for the shortened sentence of a source with this many words.

    The prompt asks for 10 to 20 words; the check allows a little more either way. A source
    under the picker's minimum (0032) may not be shortened to 10 words, so its shortened
    sentence only has to be no longer than the source, or the chunk would fail on every run.
    """
    if source_words < SOURCE_MIN_WORDS:
        return (1, source_words)
    return (MIN_WORDS, MAX_WORDS)


def _contains_lemma(text: str, lemma: str) -> bool:
    # Folding umlauts lets plurals such as Anträge match the lemma antrag.
    return lemma.lower().translate(_FOLD) in text.lower().translate(_FOLD)


def problems(request: CardRequest, content: CardContent) -> list[str]:
    """Every sanity check the content fails, as messages; empty when it passes."""
    key = request.key
    found: list[str] = []
    if not _contains_lemma(content.shortened_sentence, key.noun):
        found.append(f"the shortened sentence does not contain the noun {key.noun!r}")
    low, high = word_range(count_words(request.sentence))
    words = count_words(content.shortened_sentence)
    if not low <= words <= high:
        found.append(f"the shortened sentence has {words} words, expected {low} to {high}")
    # 0028: the citation form names the chunk, so it must hold the key's noun and verb.
    for part, lemma in (("noun", key.noun), ("verb", key.verb)):
        if not _contains_lemma(content.citation_form, lemma):
            found.append(f"the citation form {content.citation_form!r} lacks the {part} {lemma!r}")
    if len(content.meaning.splitlines()) > 1:
        found.append("the meaning is longer than one line")
    return found


def check_card(request: CardRequest, content: CardContent) -> CardContent:
    """The content unchanged if it passes every check. Raises `GenerationError` if not."""
    found = problems(request, content)
    if found:
        raise GenerationError(
            f"The generated card for {request.key} failed its checks: {'; '.join(found)}. "
            "It stays pending, and the next sync asks again."
        )
    return content


class CheckedProvider:
    """Decorator that runs `check_card` on everything the wrapped provider returns (0036).

    Put it inside `CachingProvider`, so content that fails is never cached. Raises what the
    wrapped provider raises, and `GenerationError` when a check fails.
    """

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model(self) -> str:
        return self._inner.model

    @property
    def prompt_version(self) -> str:
        return self._inner.prompt_version

    def generate(self, request: CardRequest) -> CardContent:
        return check_card(request, self._inner.generate(request))

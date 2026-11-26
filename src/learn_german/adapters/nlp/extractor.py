"""`NvvExtractor`: the `ChunkExtractor` for Nomen-Verb-Verbindungen (R8, R10)."""

from collections.abc import Sequence
from typing import Protocol, Self

from learn_german.adapters.nlp.keys import build_key
from learn_german.adapters.nlp.lexicon import Lexicon
from learn_german.adapters.nlp.match import find_matches
from learn_german.adapters.nlp.parse import SpacyParser
from learn_german.adapters.nlp.tokens import ParsedSentence
from learn_german.domain.models import Candidate, ChunkKey, ChunkKind

CONTEXT_RADIUS = 1
"""Sentences kept on each side of the chunk's sentence (R10)."""


class SentenceParser(Protocol):
    """Splits text into parsed sentences. `SpacyParser` in production, a stub in unit tests."""

    def parse(self, text: str) -> list[ParsedSentence]:
        """Raises `NlpModelMissingError` when the parser's model is not installed."""
        ...


class NvvExtractor:
    """Finds Nomen-Verb-Verbindungen and keys them as 0011 says.

    Each candidate holds the sentence and a context window of one sentence on each side.
    A chunk found twice in one sentence is returned once. Raises `NlpModelMissingError`
    on the first `extract` when the spaCy model is not installed.
    """

    def __init__(self, parser: SentenceParser, lexicon: Lexicon) -> None:
        self._parser = parser
        self._lexicon = lexicon

    @classmethod
    def default(cls) -> Self:
        """The extractor with spaCy's `de_core_news_lg` and the shipped word lists."""
        return cls(SpacyParser(), Lexicon.load())

    @property
    def kind(self) -> ChunkKind:
        return ChunkKind.NVV

    def extract(self, text: str) -> list[Candidate]:
        """Every NVV occurrence in the text, in text order."""
        sentences = self._parser.parse(text)
        candidates: list[Candidate] = []
        for index, sentence in enumerate(sentences):
            keys = self._keys(sentence)
            if keys:
                context = context_window(sentences, index)
                candidates += [Candidate(key, self.kind, sentence.text, context) for key in keys]
        return candidates

    def _keys(self, sentence: ParsedSentence) -> list[ChunkKey]:
        variants = self._lexicon.spelling_variants
        keys = (build_key(match, variants) for match in find_matches(sentence, self._lexicon))
        return list(dict.fromkeys(key for key in keys if key is not None))


def context_window(
    sentences: Sequence[ParsedSentence], index: int, radius: int = CONTEXT_RADIUS
) -> str:
    """The sentence at `index` with up to `radius` sentences on each side, joined by spaces."""
    window = sentences[max(0, index - radius) : index + radius + 1]
    return " ".join(sentence.text for sentence in window)

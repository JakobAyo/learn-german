"""`FakeExtractor`: a `ChunkExtractor` without spaCy."""

import re
from collections.abc import Mapping

from learn_german.domain.models import Candidate, ChunkKey, ChunkKind

DEFAULT_TRIGGERS: Mapping[str, ChunkKey] = {
    "Entscheidung": ChunkKey("entscheidung|treffen"),
    "Verfügung": ChunkKey("verfügung|zu|stellen"),
    "Stellung": ChunkKey("stellung|nehmen"),
    "Kritik": ChunkKey("kritik|üben"),
}
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class FakeExtractor:
    """Implements `ports.ChunkExtractor` with trigger words instead of a parse.

    Splits the text into sentences after `.`, `!` or `?`, and finds a chunk in every sentence
    that contains one of its trigger words, with the sentence either side as context, like
    `NvvExtractor`. Each trigger counts once per sentence. `texts` records every call.
    """

    def __init__(self, triggers: Mapping[str, ChunkKey] = DEFAULT_TRIGGERS) -> None:
        self.triggers = dict(triggers)
        self.texts: list[str] = []

    @property
    def kind(self) -> ChunkKind:
        return ChunkKind.NVV

    def extract(self, text: str) -> list[Candidate]:
        self.texts.append(text)
        sentences = [s for s in _SENTENCE_END.split(text.strip()) if s]
        candidates = []
        for index, sentence in enumerate(sentences):
            context = " ".join(sentences[max(0, index - 1) : index + 2])
            candidates += [
                Candidate(key, self.kind, sentence, context)
                for word, key in self.triggers.items()
                if word in sentence
            ]
        return candidates

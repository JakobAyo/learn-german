"""`FakeSource`: an in-memory `SourceAdapter`."""

import hashlib
from collections.abc import Mapping

from learn_german.domain.errors import SourceFetchError
from learn_german.domain.models import Source, SourceKind
from learn_german.ports import Clock
from tests.fakes.clock import FixedClock

PREFIX = "fake:"


class FakeSource:
    """Implements `ports.SourceAdapter` from a dict of texts, without files or network.

    Handles references that start with `fake:`. `fetch` returns the text stored under the
    reference, as a news source titled after it, and raises `SourceFetchError` for unknown
    references and for those in `fail`. Every fetched reference is recorded in `fetched`.
    """

    def __init__(self, texts: Mapping[str, str] | None = None, clock: Clock | None = None) -> None:
        self.texts: dict[str, str] = dict(texts or {})
        self.fail: dict[str, str] = {}
        self.fetched: list[str] = []
        self._clock = clock or FixedClock()

    def can_handle(self, ref: str) -> bool:
        return ref.startswith(PREFIX)

    def fetch(self, ref: str) -> Source:
        self.fetched.append(ref)
        if ref in self.fail:
            raise SourceFetchError(self.fail[ref])
        if ref not in self.texts:
            raise SourceFetchError(f"{ref} does not exist")
        text = self.texts[ref]
        return Source(
            ref=ref,
            kind=SourceKind.NEWS_URL,
            title=ref.removeprefix(PREFIX),
            fetched_at=self._clock.now(),
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
            text=text,
        )

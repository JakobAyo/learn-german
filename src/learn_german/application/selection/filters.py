"""Filters between the pending chunks and the ranker (R11, R14)."""

from collections.abc import Iterable, Sequence
from dataclasses import replace

from learn_german.domain.models import NoteKind, PendingChunk
from learn_german.ports import AnkiGateway, CandidateFilter


class FilterChain:
    """Composite `CandidateFilter`: each filter gets what the one before it let through.

    Known-item filters (R14) are appended here, so `sync` does not change. An empty chain
    passes every chunk; `sync --dry-run` uses one when Anki is unreachable. Once no chunk is
    left, later filters are not called, so their backends are not asked for nothing.
    Raises whatever its filters raise.
    """

    def __init__(self, filters: Iterable[CandidateFilter] = ()) -> None:
        self._filters = tuple(filters)

    def apply(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        remaining = list(chunks)
        for chunk_filter in self._filters:
            if not remaining:
                break
            remaining = chunk_filter.apply(remaining)
        return remaining


class AlreadyInDeckFilter:
    """Narrows each chunk's missing note kinds to those Anki does not have yet (R11, 0033).

    "Already in the deck" means a note of that kind's note type anywhere in the collection,
    not only in the tool's deck (0039). A chunk whose missing notes all exist already is
    dropped. The gateway is asked once per note kind that some chunk still needs. Raises
    `FatalError` if Anki is unreachable.
    """

    def __init__(self, gateway: AnkiGateway) -> None:
        self._gateway = gateway

    def apply(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        needed = {kind for chunk in chunks for kind in chunk.missing}
        in_deck = {kind: self._gateway.existing_keys(kind) for kind in NoteKind if kind in needed}
        kept = []
        for chunk in chunks:
            missing = frozenset(kind for kind in chunk.missing if chunk.key not in in_deck[kind])
            if missing:
                kept.append(replace(chunk, missing=missing))
        return kept

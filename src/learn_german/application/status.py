"""`ShowStatus`: the `status` command's use case (0017)."""

from dataclasses import dataclass
from datetime import datetime

from learn_german.domain.models import NoteKind, PendingChunk, SourceKind
from learn_german.ports import Ranker, UnitOfWork

DEFAULT_TOP = 10
DEFAULT_RECENT = 5


@dataclass(frozen=True, slots=True)
class SourceSummary:
    """One stored source as `status` lists it."""

    ref: str
    kind: SourceKind
    title: str | None
    fetched_at: datetime
    occurrences: int


@dataclass(frozen=True, slots=True)
class StatusReport:
    """Stored sources and pending chunks, read from SQLite only."""

    source_count: int
    recent_sources: tuple[SourceSummary, ...]
    """The most recently added sources, newest first."""
    pending: int
    """Chunks with neither note pushed yet."""
    partial: int
    """Chunks with some but not all of their notes pushed (none while there is one kind, 0049)."""
    top_chunks: tuple[PendingChunk, ...]
    """The best-ranked pending and partial chunks, best first."""


class ShowStatus:
    """Report stored sources and the pending chunks in the order `sync` would take them.

    Ranks with the same `Ranker` as `sync` but does not ask Anki, so a chunk that Anki
    already has can show as pending here; `sync` skips it (0033). Raises `DatabaseError`.
    """

    def __init__(self, uow: UnitOfWork, ranker: Ranker) -> None:
        self._uow = uow
        self._ranker = ranker

    def run(self, *, top: int = DEFAULT_TOP, recent: int = DEFAULT_RECENT) -> StatusReport:
        """Call outside any `with uow:` block. Raises ValueError if `top` or `recent` < 0."""
        if top < 0 or recent < 0:
            raise ValueError("top and recent must not be negative")
        with self._uow:
            sources = self._uow.sources.all()
            latest = sources[::-1][:recent]
            summaries = tuple(
                SourceSummary(
                    source.ref,
                    source.kind,
                    source.title,
                    source.fetched_at,
                    len(self._uow.candidates.for_source(source_id)),
                )
                for source_id, source in latest
            )
            chunks = self._uow.candidates.pending_chunks()
        partial = sum(chunk.missing != frozenset(NoteKind) for chunk in chunks)
        return StatusReport(
            source_count=len(sources),
            recent_sources=summaries,
            pending=len(chunks) - partial,
            partial=partial,
            top_chunks=tuple(self._ranker.rank(chunks)[:top]),
        )

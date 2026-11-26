"""`Reextract`: the `reextract` command's use case (0017)."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from learn_german.application.extraction import (
    CandidateChanges,
    extract_candidates,
    refresh_candidates,
)
from learn_german.ports import ChunkExtractor, UnitOfWork


@dataclass(frozen=True, slots=True)
class ReextractOutcome:
    """What extracting one stored source again changed."""

    ref: str
    title: str | None
    changes: CandidateChanges


class Reextract:
    """Run the extractors again over every stored source's text, without fetching.

    Used after the extractor or the light-verb list changed. Candidates found again are
    kept, new ones are added, vanished ones are removed unless their chunk has notes (0017).
    Each source is updated in its own unit of work. Raises `FatalError` (for example
    `NlpModelMissingError`) and stops; sources already done stay updated.
    """

    def __init__(self, uow: UnitOfWork, extractors: Sequence[ChunkExtractor]) -> None:
        self._uow = uow
        self._extractors = tuple(extractors)

    def run(self) -> Iterator[ReextractOutcome]:
        """One outcome per stored source, oldest first. Call outside any `with uow:` block."""
        with self._uow:
            sources = self._uow.sources.all()
        for source_id, source in sources:
            fresh = extract_candidates(self._extractors, source.text)
            with self._uow:
                changes = refresh_candidates(self._uow, source_id, fresh)
            yield ReextractOutcome(source.ref, source.title, changes)

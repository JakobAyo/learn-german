"""`ChunkSelector`: which chunks one sync generates, and from which sentence (R11 to R14)."""

import logging
from dataclasses import dataclass

from learn_german.application.selection.cap import cap
from learn_german.domain.models import Candidate, CardRequest, PendingChunk
from learn_german.ports import CandidateFilter, OccurrencePicker, Ranker, UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SelectedChunk:
    """A chunk chosen for this run, the note kinds it still needs, and its source sentence."""

    chunk: PendingChunk
    occurrence: Candidate

    def card_request(self) -> CardRequest:
        """The LLM request for this chunk, built from the picked occurrence (0012)."""
        return CardRequest(
            key=self.chunk.key,
            kind=self.chunk.kind,
            sentence=self.occurrence.sentence,
            context=self.occurrence.context,
        )


class ChunkSelector:
    """Filters, ranks and caps the pending chunks, then picks one occurrence for each.

    Opens its own unit-of-work blocks, so call it outside any `with uow:`. The database is not
    held while the filters ask Anki. Raises `FatalError` if a filter's backend is down, and
    ValueError if the limit is negative.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        chunk_filter: CandidateFilter,
        ranker: Ranker,
        picker: OccurrencePicker,
    ) -> None:
        self._uow = uow
        self._filter = chunk_filter
        self._ranker = ranker
        self._picker = picker

    def select(self, limit: int) -> list[SelectedChunk]:
        """Up to `limit` chunks, best first (R12, R13)."""
        with self._uow:
            pending = self._uow.candidates.pending_chunks()
        passed = self._filter.apply(pending)
        chosen = cap(self._ranker.rank(passed), limit)
        logger.info(
            "Selected %d of %d pending chunks (%d left after filtering, cap %d)",
            len(chosen),
            len(pending),
            len(passed),
            limit,
        )
        with self._uow:
            occurrences = {chunk.key: self._uow.candidates.for_key(chunk.key) for chunk in chosen}
        selected = []
        for chunk in chosen:
            if not occurrences[chunk.key]:
                # Another command (reextract) removed its last occurrence in the meantime.
                logger.warning(
                    "Skipping %s: it no longer occurs in any source (reextract removed it)",
                    chunk.key,
                )
                continue
            picked = self._picker.pick(occurrences[chunk.key])
            logger.debug(
                "%s: %d occurrences, picked the sentence of %d characters",
                chunk.key,
                len(occurrences[chunk.key]),
                len(picked.sentence),
            )
            selected.append(SelectedChunk(chunk, picked))
        return selected

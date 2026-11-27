"""`OccurrenceRanker`: the v1 `Ranker` (R13, 0034)."""

from collections.abc import Sequence

from learn_german.domain.models import NoteKind, PendingChunk

_ALL_NOTE_KINDS = frozenset(NoteKind)


class OccurrenceRanker:
    """Ranks chunks for the cap: partial chunks first, then most occurrences, then by key.

    A partial chunk already has some of its notes in Anki, so finishing it costs no new LLM
    call and leaves no half-drilled chunk behind (0014). Occurrences are counted across the
    learner's own sources (R13, 0009). The key breaks ties, so the order never depends on how
    the input was ordered (0034). `status` is meant to reuse it on
    `CandidateRepository.pending_chunks()` for its top-pending list, without asking Anki.
    """

    def rank(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        return sorted(chunks, key=_rank_key)


def _rank_key(chunk: PendingChunk) -> tuple[bool, int, str]:
    is_new = chunk.missing == _ALL_NOTE_KINDS
    return (is_new, -chunk.occurrences, chunk.key.value)

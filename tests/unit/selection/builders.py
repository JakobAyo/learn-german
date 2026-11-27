"""Small builders for selection tests. Sentences are hand-written German (R28)."""

from collections.abc import Iterable

from learn_german.domain.models import Candidate, ChunkKey, ChunkKind, NoteKind, PendingChunk

DECISION = ChunkKey("entscheidung|treffen")
DISPOSAL = ChunkKey("verfügung|zu|stellen")
FORCE = ChunkKey("kraft|in|treten")
ROLE = ChunkKey("rolle|spielen")

ALL_KINDS = frozenset(NoteKind)


def pending(
    key: ChunkKey, occurrences: int = 1, missing: Iterable[NoteKind] = ALL_KINDS
) -> PendingChunk:
    return PendingChunk(key, ChunkKind.NVV, occurrences, frozenset(missing))


def occurrence(sentence: str, key: ChunkKey = DECISION, context: str = "") -> Candidate:
    return Candidate(key, ChunkKind.NVV, sentence, context or sentence)

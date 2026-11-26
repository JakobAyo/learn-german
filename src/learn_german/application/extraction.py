"""Run the extractors over a text and reconcile the result with stored candidates (0017).

Shared by `add` and `reextract`: a new source stores every candidate found, and a source
extracted again (by `reextract` or `add --force`) follows the four 0017 rules, worked out
by `plan_candidate_changes`.
"""

from collections.abc import Iterable, Sequence, Set
from dataclasses import dataclass

from learn_german.domain.models import Candidate, ChunkKey, SourceId
from learn_german.ports import ChunkExtractor, UnitOfWork


def extract_candidates(extractors: Sequence[ChunkExtractor], text: str) -> list[Candidate]:
    """Every extractor's candidates, extractor by extractor, each in text order.

    Raises whatever the extractors raise, such as `NlpModelMissingError`.
    """
    return [candidate for extractor in extractors for candidate in extractor.extract(text)]


@dataclass(frozen=True, slots=True)
class CandidateChanges:
    """What extracting one source again did to its stored candidates (0017).

    An occurrence is identified by its chunk key and sentence within the source.
    """

    kept: tuple[Candidate, ...] = ()
    """Found again. They keep their row, so their age and their chunk's status stay."""
    added: tuple[Candidate, ...] = ()
    """Found for the first time; their chunks are pending unless notes exist already."""
    removed: tuple[Candidate, ...] = ()
    """No longer found, and their chunk has no notes: deleted."""
    retained: tuple[Candidate, ...] = ()
    """No longer found, but their chunk has notes: kept as the record of those notes."""


def plan_candidate_changes(
    stored: Iterable[Candidate], fresh: Iterable[Candidate], keys_with_notes: Set[ChunkKey]
) -> CandidateChanges:
    """Sort one source's stored and freshly extracted candidates into the four 0017 cases.

    Kept and added hold the fresh candidates, so a changed context replaces the stored one.
    Duplicates in `fresh` count once.
    """
    stored_by_id = {_identity(candidate): candidate for candidate in stored}
    fresh_by_id = {_identity(candidate): candidate for candidate in fresh}
    vanished = [c for occurrence, c in stored_by_id.items() if occurrence not in fresh_by_id]
    return CandidateChanges(
        kept=tuple(c for occurrence, c in fresh_by_id.items() if occurrence in stored_by_id),
        added=tuple(c for occurrence, c in fresh_by_id.items() if occurrence not in stored_by_id),
        removed=tuple(c for c in vanished if c.key not in keys_with_notes),
        retained=tuple(c for c in vanished if c.key in keys_with_notes),
    )


def refresh_candidates(
    uow: UnitOfWork, source_id: SourceId, fresh: Sequence[Candidate]
) -> CandidateChanges:
    """Apply `plan_candidate_changes` to a stored source. Call inside `with uow:`.

    "Has notes" means the key has at least one row in the pushed-notes record (0025).
    """
    stored = uow.candidates.for_source(source_id)
    keys = {candidate.key for candidate in stored}
    keys_with_notes = {key for key in keys if uow.chunk_states.get(key).pushed}
    changes = plan_candidate_changes(stored, fresh, keys_with_notes)
    uow.candidates.remove(source_id, changes.removed)
    uow.candidates.add_all(source_id, changes.kept + changes.added)
    return changes


def _identity(candidate: Candidate) -> tuple[ChunkKey, str]:
    return candidate.key, candidate.sentence

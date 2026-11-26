"""`AddSources`: the `add` command's use case (R4 to R6, 0017, 0042)."""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

from learn_german.application.extraction import extract_candidates, refresh_candidates
from learn_german.domain.errors import ItemError, SourceFetchError
from learn_german.domain.models import Candidate, ChunkKey, Source, SourceId
from learn_german.ports import ChunkExtractor, SourceAdapter, UnitOfWork


class AddResult(StrEnum):
    """What `add` did with one reference."""

    ADDED = "added"
    """A new source: its text and every candidate found are stored."""
    REFRESHED = "refreshed"
    """A known source fetched again with `--force`: text replaced, candidates per 0017."""
    SKIPPED = "skipped"
    """A known source, recognised by its reference or its text (R6). Not a failure."""
    FAILED = "failed"
    """The source could not be read; nothing was stored for it."""


@dataclass(frozen=True, slots=True)
class SourceOutcome:
    """The result of adding one reference, as the per-source report shows it."""

    ref: str
    result: AddResult
    title: str | None = None
    occurrences: int = 0
    """Chunk occurrences found in the text."""
    chunks: int = 0
    """Distinct chunk keys among them."""
    new_chunks: int = 0
    """Chunk keys that no stored source had before."""
    message: str | None = None
    """Why the source was skipped or failed."""


@dataclass(frozen=True, slots=True)
class AddSummary:
    """All outcomes of one `add`, in the order the references were given."""

    outcomes: tuple[SourceOutcome, ...]

    def count(self, result: AddResult) -> int:
        return sum(outcome.result is result for outcome in self.outcomes)

    @property
    def has_failures(self) -> bool:
        return self.count(AddResult.FAILED) > 0


class AddSources:
    """Fetch or read sources, extract their chunks and store both, one source at a time.

    Each reference goes to the first source adapter whose `can_handle` accepts it. A known
    source is skipped without fetching when its reference is stored, or after fetching when
    its text is, unless `force` is set; then it is fetched again, its stored text replaced
    and its candidates updated by the 0017 rules. Each source is stored in its own unit of
    work, so a failure loses only that source (0014). An `ItemError` becomes a FAILED outcome
    and the next reference is processed; a `FatalError` propagates and stops the command.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        sources: Sequence[SourceAdapter],
        extractors: Sequence[ChunkExtractor],
    ) -> None:
        self._uow = uow
        self._sources = tuple(sources)
        self._extractors = tuple(extractors)

    def run(self, refs: Iterable[str], *, force: bool = False) -> Iterator[SourceOutcome]:
        """One outcome per reference, yielded as soon as that source is done.

        Call outside any `with uow:` block; each source opens its own.
        """
        for ref in refs:
            try:
                yield self._add(ref, force=force)
            except ItemError as exc:
                yield SourceOutcome(ref, AddResult.FAILED, message=str(exc))

    def _add(self, ref: str, *, force: bool) -> SourceOutcome:
        adapter = self._adapter_for(ref)
        # R6: a known URL is not fetched again. Files are recognised after reading, below,
        # because their stored reference is the absolute path.
        if not force and self._stored_id(ref=ref) is not None:
            return _skipped(ref, None)
        source = adapter.fetch(ref)
        stored_id = self._stored_id(ref=source.ref, content_hash=source.content_hash)
        if stored_id is not None and not force:
            return _skipped(ref, source.title)
        candidates = extract_candidates(self._extractors, source.text)
        with self._uow:
            new_chunks = self._unseen_keys(candidates)
            if stored_id is None:
                self._store(source, candidates)
            else:
                self._uow.sources.replace(stored_id, source)
                refresh_candidates(self._uow, stored_id, candidates)
        return SourceOutcome(
            ref,
            AddResult.ADDED if stored_id is None else AddResult.REFRESHED,
            title=source.title,
            occurrences=len(candidates),
            chunks=len({candidate.key for candidate in candidates}),
            new_chunks=len(new_chunks),
        )

    def _adapter_for(self, ref: str) -> SourceAdapter:
        for adapter in self._sources:
            if adapter.can_handle(ref):
                return adapter
        raise SourceFetchError(
            f"learn-german cannot read {ref}. Give an http or https address of an article, "
            "or the path of a UTF-8 .txt file."
        )

    def _stored_id(self, *, ref: str, content_hash: str | None = None) -> SourceId | None:
        """The stored source with this reference, else the one with this text."""
        with self._uow:
            by_ref = self._uow.sources.find_id(ref=ref)
            if by_ref is not None or content_hash is None:
                return by_ref
            return self._uow.sources.find_id(content_hash=content_hash)

    def _unseen_keys(self, candidates: Sequence[Candidate]) -> set[ChunkKey]:
        keys = {candidate.key for candidate in candidates}
        return {key for key in keys if not self._uow.candidates.for_key(key)}

    def _store(self, source: Source, candidates: Sequence[Candidate]) -> None:
        source_id = self._uow.sources.add(source)
        self._uow.candidates.add_all(source_id, candidates)


def _skipped(ref: str, title: str | None) -> SourceOutcome:
    return SourceOutcome(
        ref,
        AddResult.SKIPPED,
        title=title,
        message="already added (same address or same text); --force fetches it again",
    )

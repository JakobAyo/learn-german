"""Protocols that use cases depend on and adapters implement (0018).

Adapters and fakes satisfy these structurally; nothing inherits from them. Each method's
docstring says which errors it raises, using the hierarchy in `domain.errors`.
"""

from collections.abc import Iterable, Sequence
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self

from learn_german.domain.models import (
    Candidate,
    CardContent,
    CardRequest,
    ChunkKey,
    ChunkKind,
    ChunkState,
    NoteDraft,
    NoteKind,
    PendingChunk,
    RunId,
    Source,
    SourceId,
)

# --- Pipeline plug-ins -----------------------------------------------------------------------


class SourceAdapter(Protocol):
    """Turns a URL or path into a `Source` with plain text (R4, R5)."""

    def can_handle(self, ref: str) -> bool:
        """Whether this adapter accepts the reference. The first adapter that does wins."""
        ...

    def fetch(self, ref: str) -> Source:
        """Fetch or read the source. Raises `ItemError` when this source cannot be read."""
        ...


class ChunkExtractor(Protocol):
    """Finds chunks of one kind in a text (R8, R9)."""

    @property
    def kind(self) -> ChunkKind: ...

    def extract(self, text: str) -> Sequence[Candidate]:
        """Every occurrence of a chunk in the text, in text order."""
        ...


class CandidateFilter(Protocol):
    """Drops chunks or narrows the note kinds they still need (R11, R14)."""

    def apply(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        """The chunks that pass, in input order. Raises `FatalError` if its backend is down."""
        ...


class Ranker(Protocol):
    """Orders chunks so the cap keeps the most useful ones (R13)."""

    def rank(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        """The same chunks, best first, with ties broken deterministically."""
        ...


class LLMProvider(Protocol):
    """Generates card content for one chunk (R17, 0004).

    Decorators such as the cache and the sanity checks wrap a provider and pass `name`,
    `model` and `prompt_version` through, so they look like the provider they wrap.
    """

    @property
    def name(self) -> str:
        """Provider name used in tags and cache keys, for example `anthropic`."""
        ...

    @property
    def model(self) -> str:
        """Model ID used in tags and cache keys, for example `claude-opus-5-5`."""
        ...

    @property
    def prompt_version(self) -> str:
        """Version of the prompt the provider sends. A new version invalidates the cache (0035)."""
        ...

    def generate(self, request: CardRequest) -> CardContent:
        """Content for one chunk's notes.

        Raises `FatalError` when every further call would fail too (bad key, unknown model,
        no credit) and `ItemError` when only this chunk failed (unusable output, a server
        error after retries).
        """
        ...


class AnkiGateway(Protocol):
    """The tool's deck and note types in Anki (R19, R20)."""

    def ensure_setup(self) -> None:
        """Create the deck and missing note types. Raises `FatalError` if Anki is unreachable
        or an existing note type has different fields."""
        ...

    def existing_keys(self, note_kind: NoteKind) -> frozenset[ChunkKey]:
        """Chunk keys that already have a note of this kind's note type anywhere in the
        collection, not only in the deck (0039)."""
        ...

    def add_notes(self, drafts: Sequence[NoteDraft]) -> None:
        """Add the notes. Raises `ItemError` if Anki rejects one, `FatalError` if unreachable."""
        ...


class Clock(Protocol):
    """Current time, injected so run IDs and timestamps are testable."""

    def now(self) -> datetime:
        """The current time, timezone-aware, in UTC."""
        ...


class OccurrencePicker(Protocol):
    """Chooses which occurrence of a chunk feeds its cards (0032)."""

    def pick(self, occurrences: Sequence[Candidate]) -> Candidate:
        """One of the occurrences, given oldest first. Raises ValueError if there are none."""
        ...


# --- Storage ---------------------------------------------------------------------------------


class SourceRepository(Protocol):
    """Processed sources and their text (R6, R24)."""

    def add(self, source: Source) -> SourceId:
        """Store a new source. Raises `DuplicateSourceError` if its ref or hash is known."""
        ...

    def get(self, source_id: SourceId) -> Source | None: ...

    def find_id(
        self, *, ref: str | None = None, content_hash: str | None = None
    ) -> SourceId | None:
        """The oldest stored source with this ref or this content hash, if any.

        Either argument may be left out, so `add` can look a URL up before fetching it.
        """
        ...

    def replace(self, source_id: SourceId, source: Source) -> None:
        """Overwrite a stored source with a fresh copy, keeping its ID and candidates (R6).

        Raises `DuplicateSourceError` if another stored source has the new ref or hash.
        """
        ...

    def all(self) -> list[tuple[SourceId, Source]]:
        """Every stored source, oldest first."""
        ...


class CandidateRepository(Protocol):
    """Every extracted chunk occurrence, pushed or not (R10, R24)."""

    def add_all(self, source_id: SourceId, candidates: Iterable[Candidate]) -> None:
        """Insert the candidates. The same key and sentence in the same source is stored once;
        adding it again updates its kind and context."""
        ...

    def remove(self, source_id: SourceId, candidates: Iterable[Candidate]) -> None:
        """Delete the source's occurrences with the same key and sentence as these (0017)."""
        ...

    def for_source(self, source_id: SourceId) -> list[Candidate]:
        """The source's candidates in the order they were first added."""
        ...

    def for_key(self, key: ChunkKey) -> list[Candidate]:
        """All occurrences of a chunk key across sources, in the order they were first added."""
        ...

    def pending_chunks(self) -> list[PendingChunk]:
        """Every chunk key with occurrences whose local state is not done, ordered by key.

        `occurrences` counts the key's candidate rows across all sources (R13). `missing` is
        the note kinds with no row in the pushed-notes record (0025); what Anki already has
        is checked later by a filter (0033). `kind` is that of the key's oldest occurrence.
        """
        ...


class ChunkStateRepository(Protocol):
    """Per-chunk progress: notes pushed and the last error (0014)."""

    def get(self, key: ChunkKey) -> ChunkState:
        """The chunk's state; a key with no record has no notes and no error."""
        ...

    def record_pushed(
        self, key: ChunkKey, note_kind: NoteKind, *, run_id: RunId, at: datetime
    ) -> None: ...

    def record_error(self, key: ChunkKey, message: str, *, at: datetime) -> None:
        """Remember why the chunk failed, replacing an earlier error."""
        ...

    def clear_error(self, key: ChunkKey) -> None: ...


class LLMCacheRepository(Protocol):
    """Raw LLM responses, so an identical request is never paid for twice (0004)."""

    def get(self, cache_key: str) -> str | None: ...

    def put(
        self,
        cache_key: str,
        response: str,
        *,
        provider: str,
        model: str,
        prompt_version: str,
        created_at: datetime,
    ) -> None:
        """Store a response, replacing any earlier one under the same key."""
        ...


class UnitOfWork(Protocol):
    """One transaction across all repositories.

    `with uow:` starts a transaction; it commits when the block ends normally and rolls back
    when the block raises. Use one block per source in `add` and per chunk in `sync`, so a
    failure loses only that item's writes (0014). Raises `DatabaseError` if the commit fails.
    """

    @property
    def sources(self) -> SourceRepository: ...

    @property
    def candidates(self) -> CandidateRepository: ...

    @property
    def chunk_states(self) -> ChunkStateRepository: ...

    @property
    def llm_cache(self) -> LLMCacheRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

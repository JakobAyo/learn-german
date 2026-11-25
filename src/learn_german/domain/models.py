"""Value objects and entities. Pure: standard library only, no I/O.

Value objects validate once at creation and are immutable, so they are safe as dict keys.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import NewType, Self

SourceId = NewType("SourceId", int)
"""Identity the storage assigns to a source when it is first stored."""


class ChunkKind(StrEnum):
    """Kind of multi-word chunk an extractor finds (R7, R9). v1 has only NVVs."""

    NVV = "nvv"


class SourceKind(StrEnum):
    """Which source adapter produced a source (R4, R5)."""

    NEWS_URL = "news-url"
    LOCAL_FILE = "local-file"


class NoteKind(StrEnum):
    """The two notes every chunk gets (0012). Anki note-type names are an adapter detail."""

    TRANSFORMATION = "transformation"
    TRANSLATION = "translation"


class ChunkStatus(StrEnum):
    """How far a chunk has got into Anki. 0014 needs none, one of two, and both told apart."""

    PENDING = "pending"
    PARTIAL = "partial"
    DONE = "done"


# --- ChunkKey (0011) -------------------------------------------------------------------------

_LEMMA = re.compile(r"[a-zäöüß]+(?:-[a-zäöüß]+)*")
_SEPARATOR = "|"
_REFLEXIVE = "sich"
# 0011: contractions are expanded (zur -> zu), so a contracted form in the preposition slot
# means the key builder skipped a step.
_CONTRACTIONS = frozenset(
    {
        "am", "ans", "aufs", "beim", "durchs", "fürs", "hinterm", "hinters", "im", "ins",
        "übers", "überm", "ums", "unterm", "unters", "vom", "vorm", "vors", "zum", "zur",
    }
)  # fmt: skip
# 0011: articles, determiners and negation are dropped from the key.
_DROPPED_WORDS = frozenset(
    {
        "der", "die", "das", "den", "dem", "des",
        "ein", "eine", "einen", "einem", "einer", "eines",
        "kein", "keine", "keinen", "keinem", "keiner", "keines", "nicht",
    }
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class ChunkKey:
    """Permanent dedupe key of an NVV: noun, optional preposition, optional sich, verb (0011).

    Raises ValueError when the value does not follow the 0011 format.
    """

    value: str

    def __post_init__(self) -> None:
        _validate_chunk_key(self.value)

    @classmethod
    def from_parts(
        cls, noun: str, verb: str, *, preposition: str | None = None, reflexive: bool = False
    ) -> Self:
        """Build a key from lemmas that are already lowercased and expanded."""
        parts = [noun, *([preposition] if preposition is not None else [])]
        parts += [*([_REFLEXIVE] if reflexive else []), verb]
        return cls(_SEPARATOR.join(parts))

    @property
    def noun(self) -> str:
        return self.value.split(_SEPARATOR)[0]

    @property
    def verb(self) -> str:
        return self.value.split(_SEPARATOR)[-1]

    @property
    def reflexive(self) -> bool:
        return self.value.split(_SEPARATOR)[-2] == _REFLEXIVE

    @property
    def preposition(self) -> str | None:
        middle = [part for part in self.value.split(_SEPARATOR)[1:-1] if part != _REFLEXIVE]
        return middle[0] if middle else None

    def __str__(self) -> str:
        return self.value


def _validate_chunk_key(value: str) -> None:
    parts = value.split(_SEPARATOR)
    if len(parts) < 2:
        raise ValueError(f"chunk key {value!r} needs at least a noun and a verb joined by '|'")
    for part in parts:
        if not _LEMMA.fullmatch(part):
            raise ValueError(f"chunk key {value!r} has an invalid lemma {part!r}")
        if part in _DROPPED_WORDS:
            raise ValueError(f"chunk key {value!r} keeps {part!r}; articles and negation drop")
    noun, *middle, verb = parts
    prepositions = middle[:-1] if middle[-1:] == [_REFLEXIVE] else middle
    if _REFLEXIVE in (noun, verb, *prepositions):
        raise ValueError(f"chunk key {value!r} may hold 'sich' only directly before the verb")
    if len(prepositions) > 1:
        raise ValueError(f"chunk key {value!r} has more than one preposition")
    if prepositions and prepositions[0] in _CONTRACTIONS:
        raise ValueError(f"chunk key {value!r} has the contraction {prepositions[0]!r}; expand it")


# --- RunId (0016) ----------------------------------------------------------------------------

_RUN_ID_FORMAT = "run-%Y%m%d-%H%M"
_RUN_ID = re.compile(r"run-\d{8}-\d{4}")


@dataclass(frozen=True, slots=True)
class RunId:
    """Identifies one sync, from its UTC start minute, for example `run-20261124-1530`.

    Raises ValueError when the value is not in that format or not a real date and time.
    """

    value: str

    def __post_init__(self) -> None:
        if not _RUN_ID.fullmatch(self.value):
            raise ValueError(f"run ID {self.value!r} must look like run-YYYYMMDD-HHMM")
        try:
            datetime.strptime(self.value, _RUN_ID_FORMAT)
        except ValueError as exc:
            raise ValueError(f"run ID {self.value!r} is not a real date and time") from exc

    @classmethod
    def from_datetime(cls, at: datetime) -> Self:
        """Run ID for a timezone-aware time, converted to UTC."""
        return cls(_require_aware(at, "run start").astimezone(UTC).strftime(_RUN_ID_FORMAT))

    def __str__(self) -> str:
        return self.value


def _require_aware(at: datetime, what: str) -> datetime:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError(f"{what} time must be timezone-aware")
    return at


# --- Entities --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Source:
    """A fetched or read text and where it came from (R5). Unique by `ref` and `content_hash`."""

    ref: str
    kind: SourceKind
    title: str | None
    fetched_at: datetime
    content_hash: str
    text: str

    def __post_init__(self) -> None:
        if not self.ref:
            raise ValueError("source ref must not be empty")
        if not self.content_hash:
            raise ValueError("source content hash must not be empty")
        _require_aware(self.fetched_at, "source fetch")


@dataclass(frozen=True, slots=True)
class Candidate:
    """One occurrence of a chunk in a source sentence, as an extractor finds it (R10)."""

    key: ChunkKey
    kind: ChunkKind
    sentence: str
    context: str

    def __post_init__(self) -> None:
        if not self.sentence:
            raise ValueError("candidate sentence must not be empty")


@dataclass(frozen=True, slots=True)
class ChunkError:
    """The last failure recorded for a chunk during a sync (0014)."""

    message: str
    failed_at: datetime


@dataclass(frozen=True, slots=True)
class ChunkState:
    """What has happened to a chunk key so far: notes pushed and the last error.

    Notes belong to the key, not to one occurrence, so progress is tracked per key.
    """

    key: ChunkKey
    pushed: frozenset[NoteKind] = frozenset()
    last_error: ChunkError | None = None

    @property
    def missing(self) -> frozenset[NoteKind]:
        """Note kinds this chunk still needs (R11: dedupe per note type)."""
        return frozenset(NoteKind) - self.pushed

    @property
    def status(self) -> ChunkStatus:
        if not self.pushed:
            return ChunkStatus.PENDING
        return ChunkStatus.PARTIAL if self.missing else ChunkStatus.DONE


@dataclass(frozen=True, slots=True)
class PendingChunk:
    """A chunk key that still needs notes, as it moves through filter, rank and cap (R11-R14)."""

    key: ChunkKey
    kind: ChunkKind
    occurrences: int
    missing: frozenset[NoteKind]


@dataclass(frozen=True, slots=True)
class CardRequest:
    """What the LLM gets for one chunk (0012). M5 may add fields."""

    key: ChunkKey
    kind: ChunkKind
    sentence: str
    context: str
    hint_language: str


@dataclass(frozen=True, slots=True)
class CardContent:
    """Validated LLM output for one chunk, enough to build both notes (0012). M5 may add fields."""

    shortened_sentence: str
    verbal_rewrite: str
    translation: str
    meaning: str


CHUNK_KEY_FIELD = "ChunkKey"


@dataclass(frozen=True, slots=True)
class NoteDraft:
    """One note ready to push. `ChunkKey` is the first field, because Anki dedupes on it."""

    note_kind: NoteKind
    key: ChunkKey
    fields: tuple[tuple[str, str], ...]
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.fields or self.fields[0] != (CHUNK_KEY_FIELD, self.key.value):
            raise ValueError(
                f"note fields must start with ({CHUNK_KEY_FIELD!r}, {self.key.value!r})"
            )
        names = [name for name, _ in self.fields]
        if len(names) != len(set(names)):
            raise ValueError(f"note fields must have unique names, got {names}")


@dataclass(frozen=True, slots=True)
class ItemFailure:
    """A chunk that failed during a run, and why."""

    key: ChunkKey
    message: str


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Outcome of one sync, printed at the end (0014)."""

    run_id: RunId
    dry_run: bool = False
    completed: tuple[ChunkKey, ...] = ()
    notes_added: int = 0
    failures: tuple[ItemFailure, ...] = ()

    @property
    def has_failures(self) -> bool:
        return bool(self.failures)

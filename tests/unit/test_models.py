from datetime import datetime

import pytest

from learn_german.domain.errors import (
    ConfigError,
    DuplicateSourceError,
    FatalError,
    ItemError,
    LearnGermanError,
    MissingCredentialsError,
)
from learn_german.domain.models import (
    Candidate,
    ChunkKey,
    ChunkKind,
    ChunkState,
    ChunkStatus,
    ItemFailure,
    NoteDraft,
    NoteKind,
    RunId,
    RunSummary,
    Source,
    SourceKind,
)
from tests.fakes.clock import DEFAULT_NOW

KEY = ChunkKey("entscheidung|treffen")


@pytest.mark.parametrize(
    ("pushed", "status", "missing"),
    [
        pytest.param(set(), ChunkStatus.PENDING, set(NoteKind), id="no-notes"),
        pytest.param(set(NoteKind), ChunkStatus.DONE, set(), id="all-notes"),
    ],
)
def test_chunk_state_status_tells_no_notes_and_all_notes_apart(
    pushed: set[NoteKind], status: ChunkStatus, missing: set[NoteKind]
) -> None:
    state = ChunkState(KEY, pushed=frozenset(pushed))

    assert (state.status, state.missing) == (status, frozenset(missing))


def _source(**changes: object) -> Source:
    values: dict[str, object] = {
        "ref": "https://example.org/a",
        "kind": SourceKind.NEWS_URL,
        "title": "Ein Titel",
        "fetched_at": DEFAULT_NOW,
        "content_hash": "abc",
        "text": "Text.",
    } | changes
    return Source(**values)  # type: ignore[arg-type]  # test helper: values vary per case


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        pytest.param({"ref": ""}, "ref", id="empty-ref"),
        pytest.param({"content_hash": ""}, "hash", id="empty-hash"),
        pytest.param({"fetched_at": datetime(2026, 1, 1)}, "timezone", id="naive-time"),
    ],
)
def test_source_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _source(**changes)


def test_candidate_rejects_empty_sentence() -> None:
    with pytest.raises(ValueError, match="sentence"):
        Candidate(KEY, ChunkKind.NVV, sentence="", context="")


def test_note_draft_accepts_chunk_key_as_first_field() -> None:
    draft = NoteDraft(
        NoteKind.TRANSFORMATION,
        KEY,
        fields=(("ChunkKey", KEY.value), ("Prompt", "Sie entschied.")),
        tags=("learn-german",),
    )

    assert draft.fields[0] == ("ChunkKey", "entscheidung|treffen")


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param((), id="no-fields"),
        pytest.param((("Prompt", "x"), ("ChunkKey", KEY.value)), id="key-not-first"),
        pytest.param((("ChunkKey", "rolle|spielen"),), id="other-key"),
    ],
)
def test_note_draft_requires_its_key_as_first_field(fields: tuple[tuple[str, str], ...]) -> None:
    with pytest.raises(ValueError, match="must start with"):
        NoteDraft(NoteKind.TRANSFORMATION, KEY, fields=fields, tags=())


def test_note_draft_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValueError, match="unique"):
        NoteDraft(
            NoteKind.TRANSFORMATION,
            KEY,
            fields=(("ChunkKey", KEY.value), ("Prompt", "a"), ("Prompt", "b")),
            tags=(),
        )


@pytest.mark.parametrize(
    ("failures", "expected"),
    [
        pytest.param((), False, id="clean"),
        pytest.param((ItemFailure(KEY, "LLM output invalid"),), True, id="one-failure"),
    ],
)
def test_run_summary_reports_failures(failures: tuple[ItemFailure, ...], expected: bool) -> None:
    summary = RunSummary(RunId("run-20261124-1530"), failures=failures)

    assert summary.has_failures is expected


@pytest.mark.parametrize(
    ("error", "base"),
    [
        pytest.param(ConfigError, FatalError, id="config"),
        pytest.param(MissingCredentialsError, FatalError, id="credentials"),
        pytest.param(DuplicateSourceError, ItemError, id="duplicate-source"),
        pytest.param(FatalError, LearnGermanError, id="fatal"),
        pytest.param(ItemError, LearnGermanError, id="item"),
    ],
)
def test_errors_belong_to_the_documented_branch(
    error: type[LearnGermanError], base: type[LearnGermanError]
) -> None:
    assert issubclass(error, base)

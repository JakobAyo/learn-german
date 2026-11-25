"""Repository and unit-of-work contract, run against an in-memory and an on-disk database."""

import sqlite3
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest

from learn_german.adapters.storage.sqlite import MEMORY, SqliteUnitOfWork, open_database
from learn_german.domain.errors import DatabaseError, DuplicateSourceError
from learn_german.domain.models import (
    Candidate,
    ChunkError,
    ChunkKey,
    ChunkKind,
    ChunkStatus,
    NoteKind,
    RunId,
    Source,
    SourceId,
    SourceKind,
)
from learn_german.ports import UnitOfWork
from tests.fakes.clock import DEFAULT_NOW

KEY = ChunkKey("entscheidung|treffen")
OTHER_KEY = ChunkKey("verfügung|zu|stellen")
RUN = RunId("run-20261124-1530")


def make_source(ref: str = "https://example.org/artikel", content_hash: str = "h1") -> Source:
    return Source(
        ref=ref,
        kind=SourceKind.NEWS_URL,
        title="Ein erfundener Artikel",
        fetched_at=DEFAULT_NOW,
        content_hash=content_hash,
        text="Die Regierung traf eine Entscheidung. Sie stellte Geld zur Verfügung.",
    )


def make_candidate(
    key: ChunkKey = KEY, sentence: str = "Die Regierung traf eine Entscheidung.", context: str = ""
) -> Candidate:
    return Candidate(key=key, kind=ChunkKind.NVV, sentence=sentence, context=context or sentence)


@pytest.fixture(params=["memory", "file"])
def connection(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[sqlite3.Connection]:
    location = MEMORY if request.param == "memory" else tmp_path / "state" / "test.db"
    connection = open_database(location)
    yield connection
    connection.close()


@pytest.fixture
def uow(connection: sqlite3.Connection) -> UnitOfWork:
    return SqliteUnitOfWork(connection)


def add_source(uow: UnitOfWork, source: Source | None = None) -> SourceId:
    with uow:
        return uow.sources.add(source or make_source())


# --- Sources ---------------------------------------------------------------------------------


def test_sources_round_trip(uow: UnitOfWork) -> None:
    source_id = add_source(uow)

    with uow:
        assert uow.sources.get(source_id) == make_source()


def test_sources_get_unknown_id_returns_none(uow: UnitOfWork) -> None:
    with uow:
        assert uow.sources.get(SourceId(42)) is None


def test_sources_store_missing_title_as_none(uow: UnitOfWork) -> None:
    source = Source(
        ref="notizen/notiz.txt",
        kind=SourceKind.LOCAL_FILE,
        title=None,
        fetched_at=DEFAULT_NOW,
        content_hash="h9",
        text="Text.",
    )
    source_id = add_source(uow, source)

    with uow:
        assert uow.sources.get(source_id) == source


@pytest.mark.parametrize(
    "duplicate",
    [
        pytest.param(make_source(content_hash="other"), id="same-ref"),
        pytest.param(make_source(ref="https://example.org/kopie"), id="same-hash"),
    ],
)
def test_sources_are_unique_by_ref_and_hash(uow: UnitOfWork, duplicate: Source) -> None:
    add_source(uow)

    with pytest.raises(DuplicateSourceError, match="already stored"), uow:
        uow.sources.add(duplicate)


@pytest.mark.parametrize(
    ("ref", "content_hash", "found"),
    [
        pytest.param("https://example.org/artikel", "nope", True, id="by-ref"),
        pytest.param("https://example.org/neu", "h1", True, id="by-hash"),
        pytest.param("https://example.org/neu", "nope", False, id="unknown"),
    ],
)
def test_sources_find_id_by_ref_or_hash(
    uow: UnitOfWork, ref: str, content_hash: str, found: bool
) -> None:
    source_id = add_source(uow)

    with uow:
        result = uow.sources.find_id(ref=ref, content_hash=content_hash)

    assert result == (source_id if found else None)


def test_sources_all_lists_oldest_first(uow: UnitOfWork) -> None:
    first = add_source(uow)
    second = add_source(uow, make_source("https://example.org/b", "h2"))

    with uow:
        assert [source_id for source_id, _ in uow.sources.all()] == [first, second]


# --- Candidates ------------------------------------------------------------------------------


def test_candidates_round_trip_in_insertion_order(uow: UnitOfWork) -> None:
    source_id = add_source(uow)
    candidates = [
        make_candidate(),
        make_candidate(OTHER_KEY, "Sie stellte Geld zur Verfügung."),
    ]

    with uow:
        uow.candidates.add_all(source_id, candidates)

    with uow:
        assert uow.candidates.for_source(source_id) == candidates


def test_candidates_upsert_same_occurrence_once(uow: UnitOfWork) -> None:
    source_id = add_source(uow)
    with uow:
        uow.candidates.add_all(source_id, [make_candidate(context="alt")])

    with uow:
        uow.candidates.add_all(source_id, [make_candidate(context="neu")])

    with uow:
        assert uow.candidates.for_source(source_id) == [make_candidate(context="neu")]


def test_candidates_keep_different_sentences_with_same_key(uow: UnitOfWork) -> None:
    source_id = add_source(uow)
    candidates = [make_candidate(), make_candidate(sentence="Wir trafen keine Entscheidung.")]

    with uow:
        uow.candidates.add_all(source_id, candidates)

    with uow:
        assert len(uow.candidates.for_source(source_id)) == 2


def test_candidates_for_key_spans_sources(uow: UnitOfWork) -> None:
    first = add_source(uow)
    second = add_source(uow, make_source("https://example.org/b", "h2"))
    with uow:
        uow.candidates.add_all(first, [make_candidate(), make_candidate(OTHER_KEY, "Andere.")])
        uow.candidates.add_all(second, [make_candidate(sentence="Er traf eine Entscheidung.")])

    with uow:
        sentences = [c.sentence for c in uow.candidates.for_key(KEY)]

    assert sentences == ["Die Regierung traf eine Entscheidung.", "Er traf eine Entscheidung."]


def test_candidates_need_a_stored_source(uow: UnitOfWork) -> None:
    with pytest.raises(DatabaseError, match="undone"), uow:
        uow.candidates.add_all(SourceId(99), [make_candidate()])


# --- Chunk states ----------------------------------------------------------------------------


def test_chunk_state_of_unknown_key_is_pending(uow: UnitOfWork) -> None:
    with uow:
        state = uow.chunk_states.get(KEY)

    assert (state.status, state.last_error) == (ChunkStatus.PENDING, None)


@pytest.mark.parametrize(
    ("kinds", "status"),
    [
        pytest.param([NoteKind.TRANSLATION], ChunkStatus.PARTIAL, id="one-of-two"),
        pytest.param(list(NoteKind), ChunkStatus.DONE, id="both"),
        pytest.param([NoteKind.TRANSLATION] * 2, ChunkStatus.PARTIAL, id="same-kind-twice"),
    ],
)
def test_chunk_state_tracks_pushed_notes(
    uow: UnitOfWork, kinds: list[NoteKind], status: ChunkStatus
) -> None:
    with uow:
        for kind in kinds:
            uow.chunk_states.record_pushed(KEY, kind, run_id=RUN, at=DEFAULT_NOW)

    with uow:
        state = uow.chunk_states.get(KEY)

    assert (state.status, state.pushed) == (status, frozenset(kinds))


def test_chunk_state_is_per_key(uow: UnitOfWork) -> None:
    with uow:
        uow.chunk_states.record_pushed(KEY, NoteKind.TRANSLATION, run_id=RUN, at=DEFAULT_NOW)

    with uow:
        assert uow.chunk_states.get(OTHER_KEY).status is ChunkStatus.PENDING


def test_chunk_state_keeps_latest_error(uow: UnitOfWork) -> None:
    later = DEFAULT_NOW + timedelta(minutes=1)
    with uow:
        uow.chunk_states.record_error(KEY, "erster Fehler", at=DEFAULT_NOW)
        uow.chunk_states.record_error(KEY, "zweiter Fehler", at=later)

    with uow:
        assert uow.chunk_states.get(KEY).last_error == ChunkError("zweiter Fehler", later)


def test_chunk_state_clear_error(uow: UnitOfWork) -> None:
    with uow:
        uow.chunk_states.record_error(KEY, "Fehler", at=DEFAULT_NOW)
        uow.chunk_states.clear_error(KEY)

    with uow:
        assert uow.chunk_states.get(KEY).last_error is None


def test_chunk_state_rejects_naive_time(uow: UnitOfWork) -> None:
    naive = DEFAULT_NOW.replace(tzinfo=None)

    with uow, pytest.raises(ValueError, match="timezone-aware"):
        uow.chunk_states.record_error(KEY, "Fehler", at=naive)


# --- LLM cache -------------------------------------------------------------------------------


def _put(uow: UnitOfWork, response: str) -> None:
    uow.llm_cache.put(
        "k1",
        response,
        provider="anthropic",
        model="claude-opus-5-5",
        prompt_version="1",
        created_at=DEFAULT_NOW,
    )


def test_llm_cache_miss_returns_none(uow: UnitOfWork) -> None:
    with uow:
        assert uow.llm_cache.get("k1") is None


def test_llm_cache_round_trip(uow: UnitOfWork) -> None:
    with uow:
        _put(uow, '{"meaning": "x"}')

    with uow:
        assert uow.llm_cache.get("k1") == '{"meaning": "x"}'


def test_llm_cache_put_replaces(uow: UnitOfWork) -> None:
    with uow:
        _put(uow, "alt")
        _put(uow, "neu")

    with uow:
        assert uow.llm_cache.get("k1") == "neu"


# --- Unit of work ----------------------------------------------------------------------------


class Boom(Exception):
    pass


def _add_then_fail(uow: UnitOfWork, source: Source) -> None:
    with uow:
        uow.sources.add(source)
        raise Boom


def _cache_then_add_duplicate(uow: UnitOfWork) -> None:
    with uow:
        _put(uow, "teuer")
        uow.sources.add(make_source())


def _fail_after_sqlite_rolled_back(connection: sqlite3.Connection, uow: UnitOfWork) -> None:
    with uow:
        uow.sources.add(make_source())
        # Disk-full and I/O errors make SQLite roll back by itself before the error arrives.
        connection.execute("ROLLBACK")
        raise sqlite3.OperationalError("database or disk is full")


def _add_orphan_with_deferred_check(connection: sqlite3.Connection, uow: UnitOfWork) -> None:
    with uow:
        # Deferred foreign keys are checked at COMMIT, so the commit itself fails.
        connection.execute("PRAGMA defer_foreign_keys = ON")
        uow.candidates.add_all(SourceId(99), [make_candidate()])


def test_uow_rolls_back_on_exception(uow: UnitOfWork) -> None:
    with pytest.raises(Boom):
        _add_then_fail(uow, make_source())

    with uow:
        assert uow.sources.all() == []


def test_uow_rolls_back_earlier_writes_when_a_repository_fails(uow: UnitOfWork) -> None:
    add_source(uow)

    with pytest.raises(DuplicateSourceError):
        _cache_then_add_duplicate(uow)

    with uow:
        assert uow.llm_cache.get("k1") is None


def test_uow_commits_each_block_separately(uow: UnitOfWork) -> None:
    add_source(uow)

    with pytest.raises(Boom):
        _add_then_fail(uow, make_source("https://example.org/b", "h2"))

    with uow:
        assert len(uow.sources.all()) == 1


def test_uow_commit_failure_is_undone(connection: sqlite3.Connection, uow: UnitOfWork) -> None:
    with pytest.raises(DatabaseError, match="Saving to the database failed"):
        _add_orphan_with_deferred_check(connection, uow)

    with uow:
        assert uow.candidates.for_key(KEY) == []


def test_uow_reports_original_error_after_sqlite_rolled_back(
    connection: sqlite3.Connection, uow: UnitOfWork
) -> None:
    with pytest.raises(DatabaseError, match="disk is full"):
        _fail_after_sqlite_rolled_back(connection, uow)

    with uow:
        assert uow.sources.all() == []


def test_uow_rejects_nesting(uow: UnitOfWork) -> None:
    with uow, pytest.raises(RuntimeError, match="already active"), uow:
        pass

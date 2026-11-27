"""ShowStatus over in-memory SQLite, ranked by OccurrenceRanker."""

from datetime import timedelta

import pytest

from learn_german.adapters.storage.sqlite import SqliteUnitOfWork
from learn_german.application.add_sources import AddSources
from learn_german.application.selection import OccurrenceRanker
from learn_german.application.status import ShowStatus, SourceSummary
from learn_german.domain.models import ChunkKey, NoteKind, RunId, SourceKind
from tests.fakes.clock import DEFAULT_NOW, FixedClock
from tests.fakes.extractors import FakeExtractor
from tests.fakes.sources import FakeSource

TEXTS = {
    "fake:a": "Der Rat traf eine Entscheidung. Sie übten Kritik.",
    "fake:b": "Die Ministerin nahm Stellung. Danach fiel die Entscheidung.",
    "fake:c": "Die Stadt stellt Geld zur Verfügung. Die Entscheidung ist gut.",
}


@pytest.fixture
def status(uow: SqliteUnitOfWork) -> ShowStatus:
    return ShowStatus(uow, OccurrenceRanker())


def add_all(uow: SqliteUnitOfWork) -> None:
    clock = FixedClock()
    source = FakeSource(TEXTS, clock)
    use_case = AddSources(uow, [source], [FakeExtractor()])
    for ref in TEXTS:
        list(use_case.run([ref]))
        clock.advance(timedelta(minutes=1))


def test_status_of_an_empty_database(status: ShowStatus) -> None:
    report = status.run()

    assert (report.source_count, report.pending, report.partial) == (0, 0, 0)
    assert report.recent_sources == ()
    assert report.top_chunks == ()


def test_status_lists_recent_sources_newest_first_with_occurrences(
    uow: SqliteUnitOfWork, status: ShowStatus
) -> None:
    add_all(uow)

    report = status.run(recent=2)

    assert report.source_count == 3
    assert report.recent_sources == (
        SourceSummary("fake:c", SourceKind.NEWS_URL, "c", DEFAULT_NOW + timedelta(minutes=2), 2),
        SourceSummary("fake:b", SourceKind.NEWS_URL, "b", DEFAULT_NOW + timedelta(minutes=1), 2),
    )


def test_status_ranks_pending_chunks_like_sync_without_done_ones(
    uow: SqliteUnitOfWork, status: ShowStatus
) -> None:
    add_all(uow)
    with uow:
        uow.chunk_states.record_pushed(
            ChunkKey("kritik|üben"),
            NoteKind.TRANSFORMATION,
            run_id=RunId("run-20261124-1530"),
            at=DEFAULT_NOW,
        )

    report = status.run(top=3)

    assert (report.pending, report.partial) == (3, 0)
    assert [(chunk.key.value, chunk.occurrences) for chunk in report.top_chunks] == [
        ("entscheidung|treffen", 3),
        ("stellung|nehmen", 1),
        ("verfügung|zu|stellen", 1),
    ]


def test_status_leaves_out_done_chunks(uow: SqliteUnitOfWork, status: ShowStatus) -> None:
    add_all(uow)
    with uow:
        for kind in NoteKind:
            uow.chunk_states.record_pushed(
                ChunkKey("entscheidung|treffen"),
                kind,
                run_id=RunId("run-20261124-1530"),
                at=DEFAULT_NOW,
            )

    report = status.run()

    assert report.pending == 3
    assert ChunkKey("entscheidung|treffen") not in {chunk.key for chunk in report.top_chunks}


def test_status_rejects_negative_limits(status: ShowStatus) -> None:
    with pytest.raises(ValueError, match="negative"):
        status.run(top=-1)

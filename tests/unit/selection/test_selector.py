"""ChunkSelector end to end over in-memory SQLite and the fake Anki deck (M4 done-when)."""

from collections.abc import Sequence

import pytest

from learn_german.application.selection import (
    AlreadyInDeckFilter,
    ChunkSelector,
    FilterChain,
    OccurrenceRanker,
    SelectedChunk,
    ShortestSentencePicker,
)
from learn_german.domain.errors import AnkiUnavailableError
from learn_german.domain.models import (
    CardRequest,
    ChunkKey,
    ChunkKind,
    NoteKind,
    PendingChunk,
    RunId,
    Source,
    SourceKind,
)
from learn_german.ports import CandidateFilter, UnitOfWork
from tests.fakes.anki import FakeAnkiGateway
from tests.fakes.clock import DEFAULT_NOW
from tests.unit.selection.builders import (
    DECISION,
    DISPOSAL,
    FORCE,
    ROLE,
    occurrence,
    pending,
)

QUESTION = ChunkKey("frage|in|stellen")
TRANSFORMATION = NoteKind.TRANSFORMATION
RUN = RunId("run-20261124-1530")

DECISION_SHORT = "Der Rat traf eine Entscheidung."
DECISION_TEN = "Nach langer Diskussion traf der Rat am Montag eine Entscheidung."
DECISION_LONG = (
    "Nach langer und teilweise heftiger Diskussion traf der Rat am Montag endlich "
    "eine Entscheidung."
)
DISPOSAL_TWELVE = "Die Stadt stellte den Schulen neue Laptops und schnelles Internet zur Verfügung."
DISPOSAL_THIRTEEN = (
    "Das Land stellte den Gemeinden im vergangenen Jahr deutlich mehr Geld zur Verfügung."
)
FORCE_SEVEN = "Das Gesetz tritt im Januar in Kraft."
QUESTION_EIGHT = "Niemand stellte die neue Regel ernsthaft in Frage."
ROLE_TEN = "Geld spielt bei dieser Frage für die meisten Menschen keine Rolle."

OLDER = [
    (DECISION, DECISION_SHORT),
    (DISPOSAL, DISPOSAL_TWELVE),
    (FORCE, FORCE_SEVEN),
    (DECISION, DECISION_TEN),
]
NEWER = [
    (DECISION, DECISION_LONG),
    (DISPOSAL, DISPOSAL_THIRTEEN),
    (ROLE, ROLE_TEN),
    (QUESTION, QUESTION_EIGHT),
]


def store(uow: UnitOfWork, ref: str, occurrences: Sequence[tuple[ChunkKey, str]]) -> None:
    source = Source(ref, SourceKind.LOCAL_FILE, None, DEFAULT_NOW, ref, "Erfundener Text.")
    with uow:
        source_id = uow.sources.add(source)
        uow.candidates.add_all(source_id, [occurrence(text, key) for key, text in occurrences])


def push_locally(uow: UnitOfWork, key: ChunkKey, *kinds: NoteKind) -> None:
    with uow:
        for kind in kinds:
            uow.chunk_states.record_pushed(key, kind, run_id=RUN, at=DEFAULT_NOW)


def selector(
    uow: UnitOfWork,
    gateway: FakeAnkiGateway | None = None,
    chunk_filter: CandidateFilter | None = None,
) -> ChunkSelector:
    if chunk_filter is None:
        chunk_filter = FilterChain([AlreadyInDeckFilter(gateway or FakeAnkiGateway())])
    return ChunkSelector(uow, chunk_filter, OccurrenceRanker(), ShortestSentencePicker())


def summary(selected: list[SelectedChunk]) -> list[tuple[ChunkKey, set[NoteKind], str]]:
    return [(s.chunk.key, set(s.chunk.missing), s.occurrence.sentence) for s in selected]


@pytest.fixture
def fixtures(uow: UnitOfWork) -> UnitOfWork:
    store(uow, "aelter.txt", OLDER)
    store(uow, "neuer.txt", NEWER)
    return uow


def test_selector_returns_expected_chunks_missing_kinds_and_order(fixtures: UnitOfWork) -> None:
    push_locally(fixtures, FORCE, TRANSFORMATION)
    gateway = FakeAnkiGateway(existing=[(TRANSFORMATION, ROLE)])

    selected = selector(fixtures, gateway).select(3)

    assert summary(selected) == [
        (DECISION, {TRANSFORMATION}, DECISION_TEN),
        (DISPOSAL, {TRANSFORMATION}, DISPOSAL_TWELVE),
        (QUESTION, {TRANSFORMATION}, QUESTION_EIGHT),
    ]


def test_selector_with_an_empty_deck_ranks_by_occurrences(fixtures: UnitOfWork) -> None:
    selected = selector(fixtures).select(10)

    assert [s.chunk.key for s in selected] == [DECISION, DISPOSAL, QUESTION, FORCE, ROLE]
    assert [s.chunk.occurrences for s in selected] == [3, 2, 1, 1, 1]


def test_selector_skips_chunks_done_locally_even_if_anki_lacks_them(fixtures: UnitOfWork) -> None:
    push_locally(fixtures, DECISION, TRANSFORMATION)

    selected = selector(fixtures).select(10)

    assert DECISION not in [s.chunk.key for s in selected]


def test_selector_with_cap_zero_selects_nothing(fixtures: UnitOfWork) -> None:
    assert selector(fixtures).select(0) == []


def test_selector_with_nothing_stored_selects_nothing(uow: UnitOfWork) -> None:
    gateway = FakeAnkiGateway()
    gateway.unavailable = True

    assert selector(uow, gateway).select(10) == []


def test_selector_stops_when_anki_is_unreachable(fixtures: UnitOfWork) -> None:
    gateway = FakeAnkiGateway()
    gateway.unavailable = True

    with pytest.raises(AnkiUnavailableError):
        selector(fixtures, gateway).select(10)


def test_selector_with_empty_filter_chain_skips_the_deck_check(fixtures: UnitOfWork) -> None:
    selected = selector(fixtures, chunk_filter=FilterChain()).select(1)

    assert summary(selected) == [(DECISION, {TRANSFORMATION}, DECISION_TEN)]


class AddsUnknownChunk:
    """Stands in for a reextract that removed a chunk's occurrences after it was listed."""

    def apply(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        return [pending(ChunkKey("rede|zu|stehen"), 9), *chunks]


def test_selector_skips_a_chunk_without_occurrences(fixtures: UnitOfWork) -> None:
    selected = selector(fixtures, chunk_filter=AddsUnknownChunk()).select(2)

    assert [s.chunk.key for s in selected] == [DECISION]


def test_selector_leaves_no_transaction_open(fixtures: UnitOfWork) -> None:
    selector(fixtures).select(10)

    with fixtures:
        assert fixtures.candidates.pending_chunks()


def test_selected_chunk_builds_the_card_request_from_its_occurrence() -> None:
    picked = occurrence(DECISION_TEN, context="Es war spät. " + DECISION_TEN)
    selected = SelectedChunk(pending(DECISION, 3), picked)

    assert selected.card_request() == CardRequest(
        key=DECISION,
        kind=ChunkKind.NVV,
        sentence=DECISION_TEN,
        context="Es war spät. " + DECISION_TEN,
    )

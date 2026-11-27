"""FilterChain and AlreadyInDeckFilter (R11, R14, 0033)."""

from collections.abc import Iterable, Sequence

import pytest

from learn_german.application.selection import AlreadyInDeckFilter, FilterChain
from learn_german.domain.errors import AnkiUnavailableError
from learn_german.domain.models import ChunkKey, NoteKind, PendingChunk
from learn_german.ports import CandidateFilter
from tests.fakes.anki import FakeAnkiGateway
from tests.unit.selection.builders import DECISION, DISPOSAL, FORCE, pending

TRANSFORMATION = NoteKind.TRANSFORMATION


class DropKey:
    """A filter that drops one key and records what it was given."""

    def __init__(self, key: ChunkKey) -> None:
        self.key = key
        self.calls: list[list[ChunkKey]] = []

    def apply(self, chunks: Sequence[PendingChunk]) -> list[PendingChunk]:
        self.calls.append([chunk.key for chunk in chunks])
        return [chunk for chunk in chunks if chunk.key != self.key]


class CountingGateway(FakeAnkiGateway):
    """The shared fake, recording which note kinds were looked up."""

    def __init__(self, existing: Iterable[tuple[NoteKind, ChunkKey]] = ()) -> None:
        super().__init__(existing)
        self.asked: list[NoteKind] = []

    def existing_keys(self, note_kind: NoteKind) -> frozenset[ChunkKey]:
        self.asked.append(note_kind)
        return super().existing_keys(note_kind)


# --- FilterChain -----------------------------------------------------------------------------


def test_empty_filter_chain_passes_every_chunk() -> None:
    chunks = [pending(DECISION), pending(FORCE)]

    assert FilterChain().apply(chunks) == chunks


def test_filter_chain_feeds_each_filter_the_previous_result() -> None:
    first, second = DropKey(DECISION), DropKey(FORCE)
    chain: CandidateFilter = FilterChain([first, second])

    result = chain.apply([pending(DECISION), pending(DISPOSAL), pending(FORCE)])

    assert [chunk.key for chunk in result] == [DISPOSAL]
    assert second.calls == [[DISPOSAL, FORCE]]


def test_filter_chain_stops_once_nothing_is_left() -> None:
    first, second = DropKey(DECISION), DropKey(FORCE)

    result = FilterChain([first, second]).apply([pending(DECISION)])

    assert (result, second.calls) == ([], [])


# --- AlreadyInDeckFilter ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("in_deck", "missing"),
    [
        pytest.param([], {TRANSFORMATION}, id="no-note-in-deck"),
        pytest.param([TRANSFORMATION], None, id="note-in-deck-dropped"),
    ],
)
def test_already_in_deck_filter_keeps_only_missing_note_kinds(
    in_deck: list[NoteKind], missing: set[NoteKind] | None
) -> None:
    gateway = FakeAnkiGateway(existing=[(kind, DECISION) for kind in in_deck])

    result = AlreadyInDeckFilter(gateway).apply([pending(DECISION)])

    assert [chunk.missing for chunk in result] == ([] if missing is None else [missing])


def test_already_in_deck_filter_never_adds_back_a_locally_pushed_kind() -> None:
    gateway = FakeAnkiGateway(existing=[(TRANSFORMATION, DECISION)])
    locally_partial = pending(DECISION, missing=[TRANSFORMATION])

    assert AlreadyInDeckFilter(gateway).apply([locally_partial]) == []


def test_already_in_deck_filter_keeps_input_order_and_counts() -> None:
    gateway = FakeAnkiGateway(existing=[(TRANSFORMATION, DISPOSAL)])
    chunks = [pending(FORCE, 3), pending(DISPOSAL, 2), pending(DECISION, 5)]

    result = AlreadyInDeckFilter(gateway).apply(chunks)

    assert [(c.key, c.occurrences) for c in result] == [(FORCE, 3), (DECISION, 5)]


def test_already_in_deck_filter_asks_only_for_needed_kinds() -> None:
    gateway = CountingGateway()

    AlreadyInDeckFilter(gateway).apply([pending(DECISION, missing=[TRANSFORMATION])])

    assert gateway.asked == [TRANSFORMATION]


def test_already_in_deck_filter_does_not_ask_anki_about_nothing() -> None:
    gateway = FakeAnkiGateway()
    gateway.unavailable = True

    assert AlreadyInDeckFilter(gateway).apply([]) == []


def test_already_in_deck_filter_fails_when_anki_is_unreachable() -> None:
    gateway = FakeAnkiGateway()
    gateway.unavailable = True

    with pytest.raises(AnkiUnavailableError):
        AlreadyInDeckFilter(gateway).apply([pending(DECISION)])

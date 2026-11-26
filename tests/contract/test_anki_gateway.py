"""AnkiGateway contract, run against FakeAnkiGateway and AnkiConnectGateway over a mock.

Both must behave the same here, so tests that use the fake can be trusted (0018). What only
the real gateway does (requests, setup details) is in tests/integration/anki/.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import pytest

from learn_german.application.notes import NoteBuilder
from learn_german.domain.errors import AnkiUnavailableError, FatalError, ItemError, PushError
from learn_german.domain.models import ChunkKey, NoteDraft, NoteKind
from learn_german.ports import AnkiGateway
from tests.fakes.anki import FakeAnkiGateway
from tests.integration.anki.mock_ankiconnect import MockAnkiConnect
from tests.unit.notes.samples import (
    CONTENT,
    DECISION,
    DISPOSAL,
    DISPOSAL_CONTENT,
    DISPOSAL_REQUEST,
    REQUEST,
    RUN,
)

TRANSFORMATION = NoteKind.TRANSFORMATION
TRANSLATION = NoteKind.TRANSLATION
BUILDER = NoteBuilder.for_run(provider="anthropic", model="claude-opus-5-5", run_id=RUN)

Existing = Iterable[tuple[NoteKind, ChunkKey]]


@dataclass
class Anki:
    """A gateway under test and a way to make its Anki unreachable."""

    gateway: AnkiGateway
    go_down: Callable[[], None]


def fake_anki(existing: Existing) -> Anki:
    fake = FakeAnkiGateway(existing)

    def go_down() -> None:
        fake.unavailable = True

    return Anki(fake, go_down)


def ankiconnect_anki(existing: Existing) -> Anki:
    mock = MockAnkiConnect()
    for note_kind, key in existing:
        mock.add_existing(note_kind, key)

    def go_down() -> None:
        mock.down = True

    return Anki(mock.gateway(), go_down)


@pytest.fixture(params=[fake_anki, ankiconnect_anki], ids=["fake", "ankiconnect"])
def make_anki(request: pytest.FixtureRequest) -> Callable[..., Anki]:
    """Builds an Anki holding the given notes, after `ensure_setup` as `sync` does."""
    factory: Callable[[Existing], Anki] = request.param

    def make(existing: Existing = ()) -> Anki:
        anki = factory(existing)
        anki.gateway.ensure_setup()
        return anki

    return make


def decision(*kinds: NoteKind) -> tuple[NoteDraft, ...]:
    return BUILDER.build(REQUEST, CONTENT, kinds or tuple(NoteKind))


def disposal(*kinds: NoteKind) -> tuple[NoteDraft, ...]:
    return BUILDER.build(DISPOSAL_REQUEST, DISPOSAL_CONTENT, kinds or tuple(NoteKind))


def test_new_deck_has_no_keys(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki().gateway

    assert gateway.existing_keys(TRANSFORMATION) == frozenset()
    assert gateway.existing_keys(TRANSLATION) == frozenset()


def test_notes_already_in_anki_are_existing_keys(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki([(TRANSFORMATION, DECISION), (TRANSLATION, DISPOSAL)]).gateway

    assert gateway.existing_keys(TRANSFORMATION) == {DECISION}
    assert gateway.existing_keys(TRANSLATION) == {DISPOSAL}


def test_added_notes_count_for_their_own_kind_only(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki().gateway

    gateway.add_notes([*decision(TRANSFORMATION), *disposal()])

    assert gateway.existing_keys(TRANSFORMATION) == {DECISION, DISPOSAL}
    assert gateway.existing_keys(TRANSLATION) == {DISPOSAL}


def test_setup_is_idempotent(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki().gateway
    gateway.add_notes(decision())

    gateway.ensure_setup()
    gateway.ensure_setup()

    assert gateway.existing_keys(TRANSFORMATION) == {DECISION}
    assert gateway.existing_keys(TRANSLATION) == {DECISION}


def test_adding_nothing_changes_nothing(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki().gateway

    gateway.add_notes([])

    assert gateway.existing_keys(TRANSFORMATION) == frozenset()


def test_adding_a_note_anki_has_is_an_item_error(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki([(TRANSLATION, DECISION)]).gateway

    with pytest.raises(PushError) as caught:
        gateway.add_notes(decision(TRANSLATION))

    assert isinstance(caught.value, ItemError)


def test_notes_before_a_rejected_note_stay_added(make_anki: Callable[..., Anki]) -> None:
    gateway = make_anki([(TRANSLATION, DECISION)]).gateway

    with pytest.raises(PushError):
        gateway.add_notes(
            [*disposal(TRANSLATION), *decision(TRANSLATION), *disposal(TRANSFORMATION)]
        )

    assert gateway.existing_keys(TRANSLATION) == {DECISION, DISPOSAL}
    assert gateway.existing_keys(TRANSFORMATION) == frozenset()


@pytest.mark.parametrize(
    "call",
    [
        lambda gateway: gateway.ensure_setup(),
        lambda gateway: gateway.existing_keys(TRANSFORMATION),
        lambda gateway: gateway.add_notes(decision()),
    ],
    ids=["ensure_setup", "existing_keys", "add_notes"],
)
def test_unreachable_anki_is_fatal(
    make_anki: Callable[..., Anki], call: Callable[[AnkiGateway], object]
) -> None:
    anki = make_anki()
    anki.go_down()

    with pytest.raises(AnkiUnavailableError) as caught:
        call(anki.gateway)

    assert isinstance(caught.value, FatalError)

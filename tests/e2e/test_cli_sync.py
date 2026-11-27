"""`sync` through typer's CliRunner: real SQLite, cache and selection; fake LLM and Anki.

Sources go in with `add`, as the owner would, through `FakeSource` and `FakeExtractor`. The
German texts are hand-written (R28).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

import pytest
from typer.testing import CliRunner

from learn_german.adapters.llm import LLMAccessError
from learn_german.adapters.storage.sqlite import SqliteUnitOfWork, open_database
from learn_german.bootstrap import Overrides
from learn_german.cli.app import EXIT_FATAL, EXIT_ITEM_FAILED, create_app
from learn_german.config import load_settings
from learn_german.domain.models import (
    CardContent,
    CardRequest,
    ChunkKey,
    ChunkState,
    NoteDraft,
    NoteKind,
)
from tests.fakes.anki import FakeAnkiGateway
from tests.fakes.clock import FixedClock
from tests.fakes.extractors import FakeExtractor
from tests.fakes.llm import FakeProvider
from tests.fakes.sources import FakeSource
from tests.integration.anki.mock_ankiconnect import DECK, MockAnkiConnect

TRANSFORMATION = NoteKind.TRANSFORMATION

DECISION = ChunkKey("entscheidung|treffen")
CRITICISM = ChunkKey("kritik|üben")
STATEMENT = ChunkKey("stellung|nehmen")
DISPOSAL = ChunkKey("verfügung|zu|stellen")

# Occurrences: Entscheidung 3, Kritik 2, Stellung 1, Verfügung 1. Ranked (0034):
# entscheidung, kritik, then the two single ones by key: stellung before verfügung.
RANKED = [DECISION, CRITICISM, STATEMENT, DISPOSAL]
TEXTS = {
    "fake:rathaus": (
        "Der Stadtrat hat am Dienstag nach langer Debatte eine wichtige Entscheidung "
        "getroffen. Die Stadt stellt dem Sportverein ab dem kommenden Mai neue Räume zur "
        "Verfügung. Die Opposition im Rathaus übte am Mittwoch scharfe Kritik an dem teuren "
        "Vorhaben."
    ),
    "fake:anwohner": (
        "Die Bürgermeisterin traf nach dem Gespräch mit den Anwohnern eine schnelle "
        "Entscheidung. Der Verband nahm in einer langen Pressekonferenz am Abend ausführlich "
        "Stellung zu den Plänen. Auch die Zeitung übte in einem Kommentar am Wochenende "
        "deutliche Kritik an der Stadt."
    ),
    "fake:berlin": (
        "Die Ministerin hat gestern in Berlin nach langen Gesprächen endlich eine Entscheidung "
        "getroffen."
    ),
}
RUN_TAGS = ("learn-german", "provider::fake", "model::fake-model", "run::run-20261124-1530")
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

runner = CliRunner()


@dataclass
class Result:
    code: int
    out: str
    err: str


@dataclass
class World:
    """The fakes behind every command of one test, so state carries over between runs."""

    anki: FakeAnkiGateway = field(default_factory=FakeAnkiGateway)
    provider: FakeProvider = field(default_factory=FakeProvider)
    with_provider: bool = True

    def overrides(self) -> Overrides:
        return Overrides(
            clock=FixedClock(),
            extractors=[FakeExtractor()],
            sources=[FakeSource(TEXTS)],
            provider=self.provider if self.with_provider else None,
            anki=self.anki,
        )

    def run(self, *args: str, overrides: Overrides | None = None) -> Result:
        app = create_app(overrides or self.overrides())
        result = runner.invoke(app, list(args))
        plain = _ANSI_ESCAPE.sub("", result.stdout), _ANSI_ESCAPE.sub("", result.stderr)
        return Result(result.exit_code, *plain)

    def add_sources(self) -> None:
        assert self.run("add", *TEXTS).code == 0

    def requested(self) -> list[ChunkKey]:
        return [request.key for request in self.provider.requests]


def pushed(anki: FakeAnkiGateway) -> list[tuple[ChunkKey, NoteKind]]:
    return [(note.key, note.note_kind) for note in anki.notes]


def chunk_state(key: ChunkKey) -> ChunkState:
    uow = SqliteUnitOfWork(open_database(load_settings().database_path))
    try:
        with uow:
            return uow.chunk_states.get(key)
    finally:
        uow.close()


@pytest.fixture
def world() -> World:
    world = World()
    world.add_sources()
    return world


# --- Happy path, cap and ranking -------------------------------------------------------------


def test_sync_pushes_one_note_per_chunk_with_the_run_tags(world: World) -> None:
    result = world.run("sync")

    assert result.code == 0
    assert pushed(world.anki) == [(key, TRANSFORMATION) for key in RANKED]
    assert {note.tags for note in world.anki.notes} == {RUN_TAGS}
    assert world.anki.setup_calls == 1
    assert "Run run-20261124-1530: 4 chunks selected." in result.out
    assert "added      entscheidung|treffen: transformation\n" in result.out
    assert "Run run-20261124-1530: 4 chunks done, 4 notes added to Anki" in result.out
    assert chunk_state(DECISION).pushed == {TRANSFORMATION}


def test_sync_puts_the_card_content_into_the_note_fields(world: World) -> None:
    world.run("sync", "--cap", "1")

    (note,) = world.anki.notes
    fields = dict(note.fields)
    assert fields["ChunkKey"] == "entscheidung|treffen"
    assert fields["Chunk"] == "entscheidung treffen"
    assert fields["Prompt"].startswith("Verbal: ")
    assert "HintLanguage" not in fields


def test_sync_respects_the_cap_and_the_ranking(world: World) -> None:
    result = world.run("sync", "--cap", "3")

    assert result.code == 0
    assert world.requested() == RANKED[:3]
    assert pushed(world.anki) == [(key, TRANSFORMATION) for key in RANKED[:3]]
    assert "3 chunks done, 3 notes added" in result.out


def test_cap_flag_overrides_the_environment(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEARN_GERMAN_CAP", "1")

    world.run("sync")
    world.run("sync", "--cap", "2")

    assert world.requested() == RANKED[:3]


def test_sync_skips_notes_anki_already_has() -> None:
    world = World(anki=FakeAnkiGateway([(TRANSFORMATION, DECISION), (TRANSFORMATION, DISPOSAL)]))
    world.add_sources()

    result = world.run("sync")

    assert result.code == 0
    assert world.requested() == [CRITICISM, STATEMENT]
    assert pushed(world.anki) == [(CRITICISM, TRANSFORMATION), (STATEMENT, TRANSFORMATION)]


# --- Dry run ---------------------------------------------------------------------------------


def test_dry_run_prints_the_notes_and_a_real_sync_reuses_the_content(world: World) -> None:
    dry = world.run("sync", "--dry-run", "--cap", "2")

    assert dry.code == 0
    assert world.anki.add_calls == 0
    assert world.anki.setup_calls == 0
    assert "Dry run run-20261124-1530: 2 chunks selected." in dry.out
    assert "would add  entscheidung|treffen: transformation\n" in dry.out
    assert "    transformation note\n      Chunk:    entscheidung treffen" in dry.out
    assert "HintLanguage" not in dry.out
    assert "2 chunks ready, 2 notes would be added.\nNothing was written to Anki." in dry.out
    assert chunk_state(DECISION).pushed == frozenset()

    real = world.run("sync", "--cap", "2")

    assert real.code == 0
    assert world.requested() == RANKED[:2]
    assert len(world.anki.notes) == 2


def test_dry_run_without_anki_warns_and_skips_the_anki_check(world: World) -> None:
    world.anki.unavailable = True

    result = world.run("sync", "--dry-run", "--cap", "1")

    assert result.code == 0
    assert "Warning: fake Anki is unavailable" in result.err
    assert "would add  entscheidung|treffen" in result.out
    assert world.requested() == [DECISION]


# --- Partial failures (0014) -----------------------------------------------------------------


def test_a_chunk_that_fails_generation_stays_pending_with_its_error(world: World) -> None:
    world.provider.fail = {CRITICISM}

    result = world.run("sync")

    assert result.code == EXIT_ITEM_FAILED
    assert [key for key, _ in pushed(world.anki)] == [DECISION, STATEMENT, DISPOSAL]
    assert "failed     kritik|üben: fake provider fails for kritik|üben" in result.out
    assert "Failed: 1 chunk. It stays pending, and the next sync tries it again:" in result.out
    state = chunk_state(CRITICISM)
    assert state.pushed == frozenset()
    assert state.last_error is not None
    assert "fake provider fails" in state.last_error.message

    world.provider.fail = set()
    retry = world.run("sync")

    assert retry.code == 0
    assert pushed(world.anki)[-1] == (CRITICISM, TRANSFORMATION)
    assert chunk_state(CRITICISM).last_error is None


def test_a_rejected_note_stays_pending_and_the_next_sync_adds_it(world: World) -> None:
    world.anki.reject = {(TRANSFORMATION, DECISION)}

    result = world.run("sync", "--cap", "1")

    assert result.code == EXIT_ITEM_FAILED
    assert pushed(world.anki) == []
    assert "failed     entscheidung|treffen: " in result.out
    state = chunk_state(DECISION)
    assert state.pushed == frozenset()
    assert state.last_error is not None

    world.anki.reject = set()
    retry = world.run("sync", "--cap", "1")

    assert retry.code == 0
    assert pushed(world.anki) == [(DECISION, TRANSFORMATION)]
    assert world.requested() == [DECISION]
    assert "added      entscheidung|treffen: transformation" in retry.out


class FailingAfter(FakeAnkiGateway):
    """Goes down after a number of `add_notes` calls, as if Anki were closed mid-run."""

    def __init__(self, calls: int) -> None:
        super().__init__()
        self.calls_left = calls

    def add_notes(self, drafts: Sequence[NoteDraft]) -> None:
        if self.calls_left == 0:
            self.unavailable = True
        self.calls_left -= 1
        super().add_notes(drafts)


def test_anki_lost_mid_run_stops_at_once_and_keeps_what_was_pushed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World(anki=FailingAfter(calls=2))
    world.add_sources()

    result = world.run("sync")

    assert result.code == EXIT_FATAL
    assert pushed(world.anki) == [(DECISION, TRANSFORMATION), (CRITICISM, TRANSFORMATION)]
    assert world.requested() == [DECISION, CRITICISM, STATEMENT]
    assert "2 chunks done, 2 notes added" in result.out
    assert "stopped early" in result.out
    assert "Error: fake Anki is unavailable" in result.err
    assert chunk_state(STATEMENT).pushed == frozenset()


class RejectedKey(FakeProvider):
    """Fails as the Claude API does when it rejects the key: every further call would too."""

    def generate(self, request: CardRequest) -> CardContent:
        self.requests.append(request)
        raise LLMAccessError("The Claude API rejected the API key. Check ANTHROPIC_API_KEY.")


def test_a_rejected_api_key_stops_the_run_at_the_first_chunk() -> None:
    world = World(provider=RejectedKey())
    world.add_sources()

    result = world.run("sync")

    assert result.code == EXIT_FATAL
    assert world.requested() == [DECISION]
    assert world.anki.notes == []
    assert "Error: The Claude API rejected the API key." in result.err
    assert chunk_state(DECISION).last_error is None


def test_a_dry_run_records_no_errors(world: World) -> None:
    world.provider.fail = {DECISION}

    result = world.run("sync", "--dry-run", "--cap", "1")

    assert result.code == EXIT_ITEM_FAILED
    assert chunk_state(DECISION).last_error is None


# --- Preflight -------------------------------------------------------------------------------


def test_unreachable_anki_stops_before_any_llm_call(world: World) -> None:
    world.anki.unavailable = True

    result = world.run("sync")

    assert result.code == EXIT_FATAL
    assert "Error: fake Anki is unavailable" in result.err
    assert world.provider.requests == []


def test_missing_api_key_is_refused_before_any_call(world: World) -> None:
    world.with_provider = False

    result = world.run("sync")

    assert result.code == EXIT_FATAL
    assert "ANTHROPIC_API_KEY is not set" in result.err
    assert world.anki.setup_calls == 0


def test_unknown_provider_is_a_config_error(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    world.with_provider = False
    monkeypatch.setenv("LEARN_GERMAN_PROVIDER", "deepseek")

    result = world.run("sync")

    assert result.code == EXIT_FATAL
    assert "Unknown LLM provider 'deepseek'" in result.err


def test_negative_cap_is_a_usage_error(world: World) -> None:
    assert world.run("sync", "--cap", "-1").code == EXIT_FATAL


# --- Repeated runs ---------------------------------------------------------------------------


def test_sync_twice_creates_no_duplicates(world: World) -> None:
    world.run("sync")

    again = world.run("sync")

    assert again.code == 0
    assert len(world.anki.notes) == 4
    assert world.anki.add_calls == 4
    assert len(world.provider.requests) == 4
    assert "Nothing to sync" in again.out


def test_status_after_sync_shows_nothing_pending(world: World) -> None:
    world.run("sync")

    assert "No chunks pending" in world.run("status").out


# --- Real gateway over a mocked AnkiConnect --------------------------------------------------


def test_sync_through_the_real_gateway_sets_up_anki_and_adds_tagged_notes(world: World) -> None:
    mock = MockAnkiConnect()
    overrides = replace(world.overrides(), anki=None, anki_http_client=mock.http_client())

    first = world.run("sync", "--cap", "1", overrides=overrides)
    second = world.run("sync", "--cap", "1", overrides=overrides)

    assert first.code == 0
    assert second.code == 0
    assert DECK in mock.decks
    assert [note.deck for note in mock.notes] == [DECK] * 2
    assert [note.fields["ChunkKey"] for note in mock.notes] == [DECISION.value, CRITICISM.value]
    assert all(note.tags == list(RUN_TAGS) for note in mock.notes)

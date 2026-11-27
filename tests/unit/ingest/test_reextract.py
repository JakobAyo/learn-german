"""Reextract and the four 0017 rules, with FakeExtractor and in-memory SQLite."""

from dataclasses import dataclass, replace

import pytest

from learn_german.adapters.storage.sqlite import SqliteUnitOfWork
from learn_german.application.extraction import CandidateChanges, plan_candidate_changes
from learn_german.application.reextract import Reextract
from learn_german.domain.errors import NlpModelMissingError
from learn_german.domain.models import Candidate, ChunkKey, ChunkKind, NoteKind, RunId
from tests.fakes.clock import DEFAULT_NOW
from tests.fakes.extractors import FakeExtractor
from tests.fakes.sources import FakeSource

KEY = ChunkKey("entscheidung|treffen")
SENTENCE = "Der Rat traf eine Entscheidung."
OCCURRENCE = Candidate(KEY, ChunkKind.NVV, SENTENCE, SENTENCE)
RUN = RunId("run-20261124-1530")


@dataclass(frozen=True, slots=True)
class Case:
    stored: bool
    """Whether the occurrence was stored before reextract."""
    found: bool
    """Whether the extractor finds it now."""
    has_notes: bool
    bucket: str
    remains: bool


CASES = [
    pytest.param(Case(stored=True, found=True, has_notes=False, bucket="kept", remains=True),
                 id="kept"),
    pytest.param(Case(stored=False, found=True, has_notes=False, bucket="added", remains=True),
                 id="new"),
    pytest.param(Case(stored=True, found=False, has_notes=False, bucket="removed", remains=False),
                 id="vanished-pending"),
    pytest.param(Case(stored=True, found=False, has_notes=True, bucket="retained", remains=True),
                 id="vanished-with-notes"),
]  # fmt: skip


_BUCKETS = ("kept", "added", "removed", "retained")


def store_source(uow: SqliteUnitOfWork, candidates: list[Candidate]) -> None:
    source = FakeSource({"fake:a": SENTENCE}).fetch("fake:a")
    with uow:
        uow.candidates.add_all(uow.sources.add(source), candidates)


@pytest.mark.parametrize("case", CASES)
def test_reextract_follows_the_four_rules(uow: SqliteUnitOfWork, case: Case) -> None:
    store_source(uow, [OCCURRENCE] if case.stored else [])
    if case.has_notes:
        with uow:
            uow.chunk_states.record_pushed(KEY, NoteKind.TRANSFORMATION, run_id=RUN, at=DEFAULT_NOW)
    extractor = FakeExtractor({"Entscheidung": KEY} if case.found else {})

    (outcome,) = Reextract(uow, [extractor]).run()

    assert outcome.ref == "fake:a"
    assert getattr(outcome.changes, case.bucket) == (OCCURRENCE,)
    assert sum(len(getattr(outcome.changes, bucket)) for bucket in _BUCKETS) == 1
    with uow:
        assert uow.candidates.for_key(KEY) == ([OCCURRENCE] if case.remains else [])
        pushed = uow.chunk_states.get(KEY).pushed
    assert pushed == ({NoteKind.TRANSFORMATION} if case.has_notes else frozenset())


def test_reextract_keeps_the_row_of_a_kept_candidate_and_updates_its_context(
    uow: SqliteUnitOfWork,
) -> None:
    other = Candidate(ChunkKey("kritik|üben"), ChunkKind.NVV, "Sie übten Kritik.", "x")
    store_source(uow, [OCCURRENCE, other])
    # Same occurrences, new context: the text around them changed.
    text = f"{SENTENCE} Sie übten Kritik."
    with uow:
        ((source_id, source),) = uow.sources.all()
        uow.sources.replace(source_id, replace(source, text=text, content_hash="changed"))

    list(Reextract(uow, [FakeExtractor({"Entscheidung": KEY, "Kritik": other.key})]).run())

    with uow:
        assert [(c.key, c.context) for c in uow.candidates.for_source(source_id)] == [
            (KEY, text),
            (other.key, text),
        ]


def test_reextract_processes_every_source_oldest_first(uow: SqliteUnitOfWork) -> None:
    source = FakeSource({"fake:a": SENTENCE, "fake:b": "Sie übten Kritik."})
    with uow:
        uow.sources.add(source.fetch("fake:a"))
        uow.sources.add(source.fetch("fake:b"))
    extractor = FakeExtractor()

    outcomes = list(Reextract(uow, [extractor]).run())

    assert [outcome.ref for outcome in outcomes] == ["fake:a", "fake:b"]
    assert extractor.texts == [SENTENCE, "Sie übten Kritik."]
    assert [len(outcome.changes.added) for outcome in outcomes] == [1, 1]


def test_reextract_stops_at_a_fatal_error(uow: SqliteUnitOfWork) -> None:
    store_source(uow, [OCCURRENCE])

    class Missing(FakeExtractor):
        def extract(self, text: str) -> list[Candidate]:
            raise NlpModelMissingError("model missing")

    with pytest.raises(NlpModelMissingError):
        list(Reextract(uow, [Missing()]).run())
    with uow:
        assert uow.candidates.for_key(KEY) == [OCCURRENCE]


def test_plan_candidate_changes_counts_duplicate_fresh_occurrences_once() -> None:
    changes = plan_candidate_changes([], [OCCURRENCE, OCCURRENCE], frozenset())

    assert changes == CandidateChanges(added=(OCCURRENCE,))

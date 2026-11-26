"""AddSources with FakeSource, FakeExtractor and in-memory SQLite."""

import pytest

from learn_german.adapters.storage.sqlite import SqliteUnitOfWork
from learn_german.application.add_sources import (
    AddResult,
    AddSources,
    AddSummary,
    SourceOutcome,
)
from learn_german.domain.errors import NlpModelMissingError
from learn_german.domain.models import Candidate, ChunkKey, NoteKind, RunId
from tests.fakes.clock import DEFAULT_NOW
from tests.fakes.extractors import FakeExtractor
from tests.fakes.sources import FakeSource

ENTSCHEIDUNG = ChunkKey("entscheidung|treffen")
VERFUEGUNG = ChunkKey("verfügung|zu|stellen")
STELLUNG = ChunkKey("stellung|nehmen")
TEXT_A = "Der Rat traf eine Entscheidung. Die Stadt stellt Geld zur Verfügung."
TEXT_B = "Die Ministerin nahm Stellung. Danach fiel die Entscheidung."


class BrokenExtractor(FakeExtractor):
    """Fails like `NvvExtractor` does without its model, on the given call."""

    def __init__(self, fail_on_call: int) -> None:
        super().__init__()
        self._fail_on_call = fail_on_call

    def extract(self, text: str) -> list[Candidate]:
        if len(self.texts) + 1 == self._fail_on_call:
            raise NlpModelMissingError("model missing")
        return super().extract(text)


@pytest.fixture
def source() -> FakeSource:
    return FakeSource({"fake:a": TEXT_A, "fake:b": TEXT_B})


def add(
    uow: SqliteUnitOfWork,
    source: FakeSource,
    *refs: str,
    force: bool = False,
    extractor: FakeExtractor | None = None,
) -> list[SourceOutcome]:
    use_case = AddSources(uow, [source], [extractor or FakeExtractor()])
    return list(use_case.run(refs, force=force))


def stored_keys(uow: SqliteUnitOfWork) -> list[str]:
    with uow:
        return sorted(chunk.key.value for chunk in uow.candidates.pending_chunks())


def test_add_sources_stores_text_and_candidates_and_reports_counts(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    (outcome,) = add(uow, source, "fake:a")

    assert outcome == SourceOutcome(
        "fake:a", AddResult.ADDED, title="a", occurrences=2, chunks=2, new_chunks=2
    )
    with uow:
        ((source_id, stored),) = uow.sources.all()
        assert (stored.text, stored.fetched_at) == (TEXT_A, DEFAULT_NOW)
        assert [c.key for c in uow.candidates.for_source(source_id)] == [ENTSCHEIDUNG, VERFUEGUNG]


def test_add_sources_counts_only_keys_no_earlier_source_had_as_new(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    first, second = add(uow, source, "fake:a", "fake:b")

    assert (first.chunks, first.new_chunks) == (2, 2)
    assert (second.chunks, second.new_chunks) == (2, 1)
    with uow:
        (entscheidung,) = [c for c in uow.candidates.pending_chunks() if c.key == ENTSCHEIDUNG]
    assert entscheidung.occurrences == 2


def test_add_sources_skips_a_known_reference_without_fetching_it(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    add(uow, source, "fake:a")

    (outcome,) = add(uow, source, "fake:a")

    assert outcome.result is AddResult.SKIPPED
    assert outcome.message is not None
    assert "--force" in outcome.message
    assert source.fetched == ["fake:a"]


def test_add_sources_skips_a_known_text_under_another_reference(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    source.texts["fake:kopie"] = TEXT_A
    add(uow, source, "fake:a")

    (outcome,) = add(uow, source, "fake:kopie")

    assert (outcome.result, outcome.title) == (AddResult.SKIPPED, "kopie")
    with uow:
        assert [stored.ref for _, stored in uow.sources.all()] == ["fake:a"]


def test_add_sources_skips_a_reference_given_twice_in_one_call(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    outcomes = add(uow, source, "fake:a", "fake:a")

    assert [outcome.result for outcome in outcomes] == [AddResult.ADDED, AddResult.SKIPPED]


def test_add_sources_force_fetches_again_and_applies_the_reextract_rules(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    add(uow, source, "fake:a")
    with uow:
        uow.chunk_states.record_pushed(
            VERFUEGUNG, NoteKind.TRANSLATION, run_id=RunId("run-20261124-1530"), at=DEFAULT_NOW
        )
    source.texts["fake:a"] = "Die Ministerin nahm Stellung."

    (outcome,) = add(uow, source, "fake:a", force=True)

    assert (outcome.result, outcome.chunks, outcome.new_chunks) == (AddResult.REFRESHED, 1, 1)
    with uow:
        ((source_id, stored),) = uow.sources.all()
        assert stored.text == "Die Ministerin nahm Stellung."
        # Entscheidung vanished and had no notes, so it went; Verfügung has a note, so it stays.
        assert [c.key for c in uow.candidates.for_source(source_id)] == [VERFUEGUNG, STELLUNG]


def test_add_sources_force_on_a_new_reference_just_adds_it(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    (outcome,) = add(uow, source, "fake:a", force=True)

    assert outcome.result is AddResult.ADDED


def test_add_sources_force_fails_when_the_new_text_belongs_to_another_source(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    add(uow, source, "fake:a", "fake:b")
    source.texts["fake:a"] = TEXT_B

    (outcome,) = add(uow, source, "fake:a", force=True)

    assert outcome.result is AddResult.FAILED
    with uow:
        assert [stored.text for _, stored in uow.sources.all()] == [TEXT_A, TEXT_B]


def test_add_sources_continues_after_a_failing_source(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    source.fail["fake:paywall"] = "fake:paywall refused access (HTTP 402)"

    outcomes = add(uow, source, "fake:a", "fake:paywall", "fake:b")

    assert [outcome.result for outcome in outcomes] == [
        AddResult.ADDED,
        AddResult.FAILED,
        AddResult.ADDED,
    ]
    assert outcomes[1].message == "fake:paywall refused access (HTTP 402)"
    summary = AddSummary(tuple(outcomes))
    assert summary.has_failures
    assert (summary.count(AddResult.ADDED), summary.count(AddResult.FAILED)) == (2, 1)
    assert stored_keys(uow) == ["entscheidung|treffen", "stellung|nehmen", "verfügung|zu|stellen"]


def test_add_sources_fails_a_reference_no_adapter_handles(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    (outcome,) = add(uow, source, "notizen.pdf")

    assert outcome.result is AddResult.FAILED
    assert outcome.message is not None
    assert ".txt file" in outcome.message
    assert not AddSummary(()).has_failures


def test_add_sources_uses_the_first_adapter_that_handles_a_reference(
    uow: SqliteUnitOfWork,
) -> None:
    first, second = FakeSource({"fake:a": TEXT_A}), FakeSource({"fake:a": TEXT_B})

    list(AddSources(uow, [first, second], [FakeExtractor()]).run(["fake:a"]))

    assert (first.fetched, second.fetched) == (["fake:a"], [])


def test_add_sources_stops_at_a_fatal_error_and_keeps_earlier_sources(
    uow: SqliteUnitOfWork, source: FakeSource
) -> None:
    use_case = AddSources(uow, [source], [BrokenExtractor(fail_on_call=2)])
    outcomes = use_case.run(["fake:a", "fake:b"])

    assert next(outcomes).result is AddResult.ADDED
    with pytest.raises(NlpModelMissingError):
        next(outcomes)
    with uow:
        assert [stored.ref for _, stored in uow.sources.all()] == ["fake:a"]

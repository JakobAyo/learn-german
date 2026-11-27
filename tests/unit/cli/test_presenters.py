"""Presenter output for the cases the end-to-end tests do not reach."""

from learn_german.application.add_sources import AddResult, AddSummary, SourceOutcome
from learn_german.application.extraction import CandidateChanges
from learn_german.application.reextract import ReextractOutcome
from learn_german.application.status import StatusReport
from learn_german.cli import presenters
from learn_german.domain.models import Candidate, ChunkKey, ChunkKind, NoteKind, PendingChunk

KEY = ChunkKey("entscheidung|treffen")
OCCURRENCE = Candidate(KEY, ChunkKind.NVV, "Der Rat traf eine Entscheidung.", "")


def test_plural() -> None:
    assert [presenters.plural(n, "chunk") for n in (0, 1, 2)] == ["0 chunks", "1 chunk", "2 chunks"]


def test_source_outcome_without_title() -> None:
    outcome = SourceOutcome("a.txt", AddResult.ADDED, occurrences=1, chunks=1, new_chunks=0)

    assert presenters.source_outcome(outcome) == "added      a.txt: 1 chunk (0 new), 1 occurrence"


def test_add_summary_of_only_skipped_sources_does_not_suggest_status() -> None:
    summary = AddSummary((SourceOutcome("a.txt", AddResult.SKIPPED, message="known"),))

    assert presenters.add_summary(summary) == "1 source: 1 skipped."


def test_status_report_marks_partial_chunks_and_handles_no_pending() -> None:
    partial = PendingChunk(KEY, ChunkKind.NVV, 2, frozenset({NoteKind.TRANSFORMATION}))
    report = StatusReport(1, (), pending=0, partial=1, top_chunks=(partial,))
    done = StatusReport(1, (), pending=0, partial=0, top_chunks=())

    assert "1 chunk pending, 1 of them with only some of their notes." in (
        presenters.status_report(report)
    )
    assert "No chunks pending" in presenters.status_report(done)


def test_reextract_outcome_mentions_candidates_kept_for_their_notes() -> None:
    outcome = ReextractOutcome("a.txt", None, CandidateChanges(retained=(OCCURRENCE,)))

    assert presenters.reextract_outcome(outcome) == (
        "a.txt: 0 kept, 0 new, 0 removed, 1 no longer found but kept for their notes"
    )

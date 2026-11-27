"""Plain-text output of the commands. Pure functions: results in, lines out.

The CLI prints what these return; nothing else in the package writes to the terminal.
"""

from learn_german.application.add_sources import AddResult, AddSummary, SourceOutcome
from learn_german.application.reextract import ReextractOutcome
from learn_german.application.status import SourceSummary, StatusReport
from learn_german.application.sync import ChunkOutcome, SyncRun
from learn_german.domain.errors import LearnGermanError
from learn_german.domain.models import (
    CHUNK_KEY_FIELD,
    NoteDraft,
    NoteKind,
    PendingChunk,
    RunSummary,
)

_RESULT_WIDTH = max(len(result.value) for result in AddResult)
_ALL_NOTE_KINDS = frozenset(NoteKind)


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def fatal_error(error: LearnGermanError) -> str:
    return f"Error: {error}"


# --- add -------------------------------------------------------------------------------------


def source_outcome(outcome: SourceOutcome) -> str:
    """One line per source, printed as soon as the source is done."""
    label = outcome.result.value.ljust(_RESULT_WIDTH)
    if outcome.result in (AddResult.ADDED, AddResult.REFRESHED):
        title = f' "{outcome.title}"' if outcome.title else ""
        return (
            f"{label}  {outcome.ref}{title}: {plural(outcome.chunks, 'chunk')} "
            f"({outcome.new_chunks} new), {plural(outcome.occurrences, 'occurrence')}"
        )
    return f"{label}  {outcome.ref}: {outcome.message}"


def add_summary(summary: AddSummary) -> str:
    counts = ", ".join(
        f"{summary.count(result)} {result.value}" for result in AddResult if summary.count(result)
    )
    total = plural(len(summary.outcomes), "source")
    lines = [f"{total}: {counts}." if counts else "No sources given."]
    if summary.count(AddResult.ADDED) or summary.count(AddResult.REFRESHED):
        lines.append("Run `learn-german status` to see the pending chunks.")
    return "\n".join(lines)


# --- status ----------------------------------------------------------------------------------


def status_report(report: StatusReport) -> str:
    if report.source_count == 0:
        return "No sources yet. Add one with `learn-german add <article URL or file.txt>`."
    lines = [f"{plural(report.source_count, 'source')} stored. Most recent:"]
    lines += [f"  {_source_line(source)}" for source in report.recent_sources]
    lines += ["", _pending_line(report)]
    if report.top_chunks:
        lines.append("Next for `sync`, best first (Anki is not checked here):")
        width = max(len(chunk.key.value) for chunk in report.top_chunks)
        lines += [
            f"  {rank:>3}. {_chunk_line(chunk, width)}"
            for rank, chunk in enumerate(report.top_chunks, start=1)
        ]
    return "\n".join(lines)


def _source_line(source: SourceSummary) -> str:
    title = f'"{source.title}" ' if source.title else ""
    added = source.fetched_at.astimezone().strftime("%Y-%m-%d")
    occurrences = plural(source.occurrences, "occurrence")
    return f"{added}  {title}({occurrences})  {source.ref}"


def _pending_line(report: StatusReport) -> str:
    total = report.pending + report.partial
    if total == 0:
        return "No chunks pending: every chunk found so far has its notes."
    partial = f", {report.partial} of them with only some of their notes" if report.partial else ""
    return f"{plural(total, 'chunk')} pending{partial}."


def _chunk_line(chunk: PendingChunk, width: int) -> str:
    line = f"{chunk.key.value.ljust(width)}  {plural(chunk.occurrences, 'occurrence')}"
    if chunk.missing != _ALL_NOTE_KINDS:
        needs = ", ".join(sorted(kind.value for kind in chunk.missing))
        line += f"  (needs {needs} note)"
    return line


# --- reextract -------------------------------------------------------------------------------


def reextract_outcome(outcome: ReextractOutcome) -> str:
    changes = outcome.changes
    line = (
        f"{outcome.ref}: {len(changes.kept)} kept, {len(changes.added)} new, "
        f"{len(changes.removed)} removed"
    )
    if changes.retained:
        line += f", {len(changes.retained)} no longer found but kept for their notes"
    return line


def reextract_summary(outcomes: list[ReextractOutcome]) -> str:
    if not outcomes:
        return "No sources stored, so there is nothing to extract again."
    added = sum(len(outcome.changes.added) for outcome in outcomes)
    removed = sum(len(outcome.changes.removed) for outcome in outcomes)
    return (
        f"Extracted {plural(len(outcomes), 'source')} again: "
        f"{plural(added, 'new occurrence')}, {removed} removed."
    )


# --- sync ------------------------------------------------------------------------------------

_SYNC_LABEL_WIDTH = len("would add")


def anki_unavailable_warning(reason: str) -> str:
    """Printed to stderr when a dry run cannot reach Anki (0046)."""
    return (
        f"Warning: {reason}\nThe dry run goes on without asking Anki which notes it already "
        "has, so it may show notes Anki would reject as duplicates."
    )


def sync_start(run: SyncRun) -> str:
    """What the run is about to do, printed before the first LLM call."""
    if not run.selected:
        return "Nothing to sync: no pending chunk needs notes. Add sources with `learn-german add`."
    mode = "Dry run" if run.dry_run else "Run"
    chunks = plural(len(run.selected), "chunk")
    return f"{mode} {run.run_id}: {chunks} selected. Tags: {' '.join(run.tags)}"


def chunk_outcome(outcome: ChunkOutcome, *, dry_run: bool) -> str:
    """One chunk's line, and in a dry run the notes it would add (R23)."""
    if outcome.error is not None:
        added = ""
        if outcome.notes:
            added = f" ({_kinds(outcome.notes)} note added)"
        return f"{'failed'.ljust(_SYNC_LABEL_WIDTH)}  {outcome.key}{added}: {outcome.error}"
    label = "would add" if dry_run else "added"
    line = f"{label.ljust(_SYNC_LABEL_WIDTH)}  {outcome.key}: {_kinds(outcome.notes)}"
    if not dry_run:
        return line
    width = max((len(name) for note in outcome.notes for name, _ in note.fields), default=0)
    return "\n".join([line, *(_note_preview(note, width) for note in outcome.notes)])


def _kinds(notes: tuple[NoteDraft, ...]) -> str:
    return ", ".join(note.note_kind.value for note in notes)


def _note_preview(note: NoteDraft, width: int) -> str:
    fields = [(name, value) for name, value in note.fields if name != CHUNK_KEY_FIELD]
    lines = [f"    {note.note_kind.value} note"]
    lines += [f"      {(name + ':').ljust(width + 1)} {value}" for name, value in fields]
    return "\n".join(lines)


def run_summary(summary: RunSummary, *, stopped: bool = False) -> str:
    """The end of a run: counts, then every failed chunk (0014)."""
    chunks = plural(len(summary.completed), "chunk")
    if summary.dry_run:
        lines = [
            f"Dry run {summary.run_id}: {chunks} ready, "
            f"{plural(summary.notes_added, 'note')} would be added.",
            "Nothing was written to Anki. The generated content is cached, so the next sync "
            "does not pay for it again.",
        ]
    else:
        lines = [
            f"Run {summary.run_id}: {chunks} done, {plural(summary.notes_added, 'note')} added "
            f"to Anki, tagged run::{summary.run_id}."
        ]
    if summary.failures:
        count = len(summary.failures)
        them = "it" if count == 1 else "them"
        lines.append(
            f"Failed: {plural(count, 'chunk')}. {'It stays' if count == 1 else 'They stay'} "
            f"pending, and the next sync tries {them} again:"
        )
        lines += [f"  {failure.key}: {failure.message}" for failure in summary.failures]
    if stopped:
        lines.append("The run stopped early because of the error below.")
    return "\n".join(lines)

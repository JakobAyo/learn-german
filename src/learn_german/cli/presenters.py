"""Plain-text output of the commands. Pure functions: results in, lines out.

The CLI prints what these return; nothing else in the package writes to the terminal.
"""

from learn_german.application.add_sources import AddResult, AddSummary, SourceOutcome
from learn_german.application.reextract import ReextractOutcome
from learn_german.application.status import SourceSummary, StatusReport
from learn_german.domain.errors import LearnGermanError
from learn_german.domain.models import NoteKind, PendingChunk

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
    partial = f", {report.partial} of them with one of their two notes" if report.partial else ""
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

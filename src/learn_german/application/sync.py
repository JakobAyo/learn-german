"""`SyncService`: one run of select, generate and push (R12, R21 to R23a, 0014, 0046, 0047).

`start` checks Anki and selects the chunks before any money is spent; the returned `SyncRun`
then generates and pushes one chunk at a time, yielding an outcome per chunk. Settings the
run needs (hint language, API key) are checked by the composition root before this exists.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from learn_german.application.notes import NoteBuilder
from learn_german.application.selection import ChunkSelector, SelectedChunk
from learn_german.domain.errors import AnkiUnavailableError, ItemError
from learn_german.domain.models import (
    ChunkKey,
    ItemFailure,
    NoteDraft,
    NoteKind,
    RunId,
    RunSummary,
)
from learn_german.ports import AnkiGateway, Clock, LLMProvider, UnitOfWork


@dataclass(frozen=True, slots=True)
class ChunkOutcome:
    """What happened to one chunk.

    `notes` are the notes added, or in a dry run the notes that would be added. `error` is
    why the chunk stopped, if it did; notes added before the error stay in Anki (0040).
    """

    key: ChunkKey
    notes: tuple[NoteDraft, ...]
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None


class SyncRun:
    """One sync after its preflight and selection. Built by `SyncService.start`.

    `chunks()` generates and pushes the selected chunks in rank order and yields each outcome
    once its state is saved, so a fatal error later loses nothing already done. An
    `ItemError` is recorded for its chunk and the run goes on; a `FatalError` (Anki gone,
    API key rejected, database failure) propagates at once. A dry run writes nothing to Anki
    and no chunk state; only the LLM cache is filled.
    """

    def __init__(
        self,
        *,
        run_id: RunId,
        dry_run: bool,
        selected: Sequence[SelectedChunk],
        anki_unavailable: str | None,
        services: "SyncService",
    ) -> None:
        self.run_id = run_id
        self.dry_run = dry_run
        self.selected = tuple(selected)
        self.anki_unavailable = anki_unavailable
        """In a dry run, why Anki could not be asked; deduplication then used local state."""
        self._services = services
        self._builder = NoteBuilder.for_run(
            provider=services.provider.name, model=services.provider.model, run_id=run_id
        )
        self._outcomes: list[ChunkOutcome] = []

    @property
    def tags(self) -> tuple[str, ...]:
        """The tags every note of this run carries (R22)."""
        return self._builder.tags

    def chunks(self) -> Iterator[ChunkOutcome]:
        for selected in self.selected:
            outcome = self._sync_chunk(selected)
            self._outcomes.append(outcome)
            yield outcome

    def summary(self) -> RunSummary:
        """The run so far: complete after `chunks()` is exhausted, partial after a fatal error."""
        return RunSummary(
            run_id=self.run_id,
            dry_run=self.dry_run,
            completed=tuple(outcome.key for outcome in self._outcomes if not outcome.failed),
            notes_added=sum(len(outcome.notes) for outcome in self._outcomes),
            failures=tuple(
                ItemFailure(outcome.key, outcome.error)
                for outcome in self._outcomes
                if outcome.error is not None
            ),
        )

    def _sync_chunk(self, selected: SelectedChunk) -> ChunkOutcome:
        services = self._services
        request = selected.card_request(services.hint_language)
        kinds = tuple(kind for kind in NoteKind if kind in selected.chunk.missing)
        pushed: list[NoteDraft] = []
        error: ItemError | None = None
        settled = False
        try:
            # Outside any unit of work: the cache opens its own (0036).
            content = services.provider.generate(request)
            drafts = self._builder.build(request, content, kinds)
            if self.dry_run:
                return ChunkOutcome(request.key, drafts)
            for draft in drafts:
                # One note per call, so the notes before a rejected one are known (0040, 0047).
                services.gateway.add_notes([draft])
                pushed.append(draft)
            settled = True
        except ItemError as exc:
            error = exc
            settled = True
        finally:
            if not self.dry_run:
                self._record(request.key, pushed, error, settled=settled)
        return ChunkOutcome(request.key, tuple(pushed), None if error is None else str(error))

    def _record(
        self, key: ChunkKey, pushed: Sequence[NoteDraft], error: ItemError | None, *, settled: bool
    ) -> None:
        """Save the notes pushed and the chunk's error in one unit of work (0014, 0025).

        `settled` is false when a fatal error interrupted the chunk: the pushed notes are
        still saved, and the chunk's error is left as it was.
        """
        if not pushed and not settled:
            return
        services = self._services
        now = services.clock.now()
        with services.uow:
            for draft in pushed:
                services.uow.chunk_states.record_pushed(
                    key, draft.note_kind, run_id=self.run_id, at=now
                )
            if error is not None:
                services.uow.chunk_states.record_error(key, str(error), at=now)
            elif settled:
                services.uow.chunk_states.clear_error(key)


class SyncService:
    """Runs `sync`: preflight, select, then generate and push chunk by chunk.

    `provider` is the full stack, `CachingProvider(CheckedProvider(...))` (0036). `selector`
    filters through Anki; `offline_selector` has no Anki filter and is used only by a dry
    run that cannot reach Anki (0033). Call `start` outside any `with uow:` block.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        gateway: AnkiGateway,
        provider: LLMProvider,
        selector: ChunkSelector,
        offline_selector: ChunkSelector,
        clock: Clock,
        hint_language: str,
    ) -> None:
        self.uow = uow
        self.gateway = gateway
        self.provider = provider
        self.selector = selector
        self.offline_selector = offline_selector
        self.clock = clock
        self.hint_language = hint_language

    def start(self, *, cap: int, dry_run: bool) -> SyncRun:
        """Check Anki, then select up to `cap` chunks. Nothing is generated yet.

        A real run sets Anki up (deck and note types); a dry run only checks that Anki
        answers and, if it does not, goes on without deduplicating against Anki. Raises
        `FatalError` if Anki is unreachable or not set up in a real run, or if selection
        cannot ask Anki, and ValueError if `cap` is negative.
        """
        run_id = RunId.from_datetime(self.clock.now())
        anki_unavailable = self._preflight(dry_run=dry_run)
        selector = self.offline_selector if anki_unavailable else self.selector
        return SyncRun(
            run_id=run_id,
            dry_run=dry_run,
            selected=selector.select(cap),
            anki_unavailable=anki_unavailable,
            services=self,
        )

    def _preflight(self, *, dry_run: bool) -> str | None:
        """Why Anki cannot be asked in a dry run, or None. Raises `FatalError` otherwise."""
        if not dry_run:
            self.gateway.ensure_setup()
            return None
        try:
            self.gateway.check_available()
        except AnkiUnavailableError as exc:
            return str(exc)
        return None

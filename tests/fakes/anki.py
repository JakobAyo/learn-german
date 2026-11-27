from collections.abc import Iterable, Sequence

from learn_german.domain.errors import AnkiUnavailableError, PushError
from learn_german.domain.models import ChunkKey, NoteDraft, NoteKind


class FakeAnkiGateway:
    """Implements `ports.AnkiGateway` with an in-memory deck.

    Created before the parallel tracks (0026) so M4 and M7 can use it; M6 owns it and runs
    the gateway contract suite against it.
    """

    def __init__(self, existing: Iterable[tuple[NoteKind, ChunkKey]] = ()) -> None:
        self.notes: list[NoteDraft] = []
        self.setup_calls = 0
        self.add_calls = 0
        self.unavailable = False
        self.reject: set[tuple[NoteKind, ChunkKey]] = set()
        self._keys: dict[NoteKind, set[ChunkKey]] = {kind: set() for kind in NoteKind}
        for note_kind, key in existing:
            self._keys[note_kind].add(key)

    def check_available(self) -> None:
        self._check_available()

    def ensure_setup(self) -> None:
        self._check_available()
        self.setup_calls += 1

    def existing_keys(self, note_kind: NoteKind) -> frozenset[ChunkKey]:
        self._check_available()
        return frozenset(self._keys[note_kind])

    def add_notes(self, drafts: Sequence[NoteDraft]) -> None:
        self._check_available()
        self.add_calls += 1
        for draft in drafts:
            if (draft.note_kind, draft.key) in self.reject:
                raise PushError(f"fake Anki rejected the {draft.note_kind} note for {draft.key}")
            if draft.key in self._keys[draft.note_kind]:
                raise PushError(f"fake Anki already has a {draft.note_kind} note for {draft.key}")
            self._keys[draft.note_kind].add(draft.key)
            self.notes.append(draft)

    def _check_available(self) -> None:
        if self.unavailable:
            raise AnkiUnavailableError("fake Anki is unavailable")

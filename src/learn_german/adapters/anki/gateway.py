"""`AnkiConnectGateway`: the tool's deck and note types through AnkiConnect (0003, 0038-0040)."""

import html
import logging
from collections.abc import Mapping, Sequence

from learn_german.adapters.anki.client import AnkiConnectClient
from learn_german.adapters.anki.errors import AnkiActionError
from learn_german.adapters.anki.note_types import NOTE_TYPES, NoteTypeSpec
from learn_german.domain.errors import NoteTypeMismatchError, PushError
from learn_german.domain.models import CHUNK_KEY_FIELD, ChunkKey, NoteDraft, NoteKind

logger = logging.getLogger(__name__)


class AnkiConnectGateway:
    """Implements `ports.AnkiGateway` over an `AnkiConnectClient`.

    `check_available` only asks for AnkiConnect's version, so it writes nothing (0046).
    `ensure_setup` checks AnkiConnect's version, creates the deck if it is missing and each
    note type that is missing. It never changes an existing note type, and raises
    `NoteTypeMismatchError` if one has other fields than its spec (0038).

    `existing_keys` counts every note of the kind's note type in the collection, not only
    in the deck, because the note type is the tool's and Anki's duplicate check covers the
    whole note type too (0039).

    `add_notes` adds one note per AnkiConnect call. A rejected note raises `PushError`; the
    notes before it stay added (0040). Every method raises `AnkiUnavailableError` when
    Anki does not answer and `AnkiActionError` when a setup or search action fails.
    """

    def __init__(
        self,
        client: AnkiConnectClient,
        *,
        deck: str,
        note_types: Mapping[NoteKind, NoteTypeSpec] = NOTE_TYPES,
    ) -> None:
        self._client = client
        self._deck = deck
        self._note_types = note_types

    def check_available(self) -> None:
        self._client.require_version()

    def ensure_setup(self) -> None:
        self._client.require_version()
        if self._deck not in _strings(self._client.invoke("deckNames"), "deckNames"):
            self._client.invoke("createDeck", deck=self._deck)
            logger.info("Created the Anki deck %s", self._deck)
        models = _strings(self._client.invoke("modelNames"), "modelNames")
        for spec in self._note_types.values():
            if spec.name in models:
                self._check_fields(spec)
            else:
                self._create_note_type(spec)

    def existing_keys(self, note_kind: NoteKind) -> frozenset[ChunkKey]:
        spec = self._note_types[note_kind]
        query = f'"note:{_escape_search(spec.name)}"'
        note_ids = self._client.invoke("findNotes", query=query)
        if not isinstance(note_ids, list):
            raise AnkiActionError("findNotes", f"expected a list of note IDs, got {note_ids!r}")
        if not note_ids:
            return frozenset()
        infos = self._client.invoke("notesInfo", notes=note_ids)
        if not isinstance(infos, list):
            raise AnkiActionError("notesInfo", f"expected a list of notes, got {infos!r}")
        return frozenset(key for info in infos if (key := _chunk_key(info, spec)) is not None)

    def add_notes(self, drafts: Sequence[NoteDraft]) -> None:
        for draft in drafts:
            note = self._note_params(draft)
            try:
                note_id = self._client.invoke("addNote", note=note)
            except AnkiActionError as exc:
                raise PushError(
                    f"Anki rejected the {draft.note_kind} note for {draft.key}: {exc.detail}. "
                    "The chunk stays pending; the next sync adds only the notes it lacks."
                ) from exc
            logger.debug("Added %s note %s for %s", draft.note_kind, note_id, draft.key)

    def _check_fields(self, spec: NoteTypeSpec) -> None:
        fields = _strings(
            self._client.invoke("modelFieldNames", modelName=spec.name), "modelFieldNames"
        )
        if tuple(fields) != spec.fields:
            raise NoteTypeMismatchError(
                f"The Anki note type {spec.name} has the fields {', '.join(fields)}, but "
                f"learn-german needs {', '.join(spec.fields)} in that order. Its notes need a "
                "migration; do not edit the note type's fields by hand. Restore them in Anki "
                "(Tools, Manage Note Types, Fields) and run the command again."
            )

    def _create_note_type(self, spec: NoteTypeSpec) -> None:
        self._client.invoke(
            "createModel",
            modelName=spec.name,
            inOrderFields=list(spec.fields),
            css=spec.css,
            isCloze=False,
            cardTemplates=[
                {"Name": card.name, "Front": card.front, "Back": card.back}
                for card in spec.templates
            ],
        )
        logger.info("Created the Anki note type %s", spec.name)

    def _note_params(self, draft: NoteDraft) -> dict[str, object]:
        """The `addNote` note. Field values are escaped, because Anki fields are HTML.

        Raises ValueError if the draft's fields are not its note type's, since AnkiConnect
        would silently drop unknown fields.
        """
        spec = self._note_types[draft.note_kind]
        names = tuple(name for name, _ in draft.fields)
        if names != spec.fields:
            raise ValueError(
                f"{draft.note_kind} note for {draft.key} has the fields {names}, "
                f"but {spec.name} has {spec.fields}"
            )
        return {
            "deckName": self._deck,
            "modelName": spec.name,
            "fields": {name: html.escape(value, quote=False) for name, value in draft.fields},
            "tags": list(draft.tags),
            "options": {"allowDuplicate": False, "duplicateScope": "collection"},
        }


def _strings(result: object, action: str) -> list[str]:
    if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
        raise AnkiActionError(action, f"expected a list of names, got {result!r}")
    return result


def _chunk_key(info: object, spec: NoteTypeSpec) -> ChunkKey | None:
    """The note's chunk key, or None (logged) if its field is missing or not a valid key."""
    value = None
    if isinstance(info, dict) and isinstance(fields := info.get("fields"), dict):
        field = fields.get(CHUNK_KEY_FIELD)
        if isinstance(field, dict) and isinstance(field.get("value"), str):
            value = html.unescape(field["value"]).strip()
    if value is None:
        logger.warning(
            "Ignoring a %s note without a %s field; restore the field in Anki (Tools, Manage "
            "Note Types) so duplicates of it can be recognised",
            spec.name,
            CHUNK_KEY_FIELD,
        )
        return None
    try:
        return ChunkKey(value)
    except ValueError:
        logger.warning(
            "Ignoring a %s note whose %s is %r, not a chunk key; fix or delete it in Anki "
            "(Browse, search %s:%s)",
            spec.name,
            CHUNK_KEY_FIELD,
            value,
            CHUNK_KEY_FIELD,
            value,
        )
        return None


def _escape_search(text: str) -> str:
    """Escape Anki search syntax inside a quoted term: backslash, quote and wildcards."""
    for char in ("\\", '"', "*", "_"):
        text = text.replace(char, "\\" + char)
    return text

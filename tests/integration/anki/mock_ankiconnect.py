"""An in-memory AnkiConnect behind `httpx2.MockTransport`, for the real gateway. No network.

It answers the actions the gateway uses the way AnkiConnect 6 does: `result` and `error`
in every answer, errors as strings, and Anki's duplicate check on a note type's first field
across the whole collection.
"""

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

import httpx2

from learn_german.adapters.anki import AnkiConnectClient, AnkiConnectGateway, NoteTypeSpec
from learn_german.adapters.anki.note_types import NOTE_TYPES
from learn_german.domain.models import CHUNK_KEY_FIELD, ChunkKey, NoteKind

URL = "http://127.0.0.1:8765"
DECK = "learn-german::chunks"

_NOTE_QUERY = re.compile(r'"note:((?:[^"\\]|\\.)*)"')
_ESCAPED = re.compile(r"\\(.)")


class ActionFailed(Exception):
    """Becomes the `error` field of the answer."""


@dataclass
class Model:
    fields: list[str]
    css: str = ""
    templates: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Note:
    note_id: int
    deck: str
    model: str
    fields: dict[str, str]
    tags: list[str]


class MockAnkiConnect:
    """A collection with decks, note types and notes, and a log of every request.

    `down` makes every request fail as if Anki were closed. `results` replaces an action's
    result and `errors` makes an action answer with an error, both by action name.
    """

    def __init__(self, *, version: int = 6, decks: Iterable[str] = ("Default",)) -> None:
        self.version = version
        self.decks = list(decks)
        self.models: dict[str, Model] = {}
        self.notes: list[Note] = []
        self.requests: list[dict[str, object]] = []
        self.down = False
        self.results: dict[str, object] = {}
        self.errors: dict[str, str] = {}

    # --- Seeding --------------------------------------------------------------------------

    def add_model(self, name: str, fields: Iterable[str], *, css: str = "") -> None:
        self.models[name] = Model(list(fields), css)

    def add_note(self, model: str, fields: Mapping[str, str], *, deck: str = DECK) -> None:
        self.notes.append(Note(len(self.notes) + 1, deck, model, dict(fields), []))

    def add_existing(self, note_kind: NoteKind, key: ChunkKey, *, deck: str = DECK) -> None:
        """A note the tool pushed earlier, in a collection where its note type may not exist."""
        self.add_note(NOTE_TYPES[note_kind].name, {CHUNK_KEY_FIELD: key.value}, deck=deck)

    # --- Wiring ---------------------------------------------------------------------------

    def http_client(self) -> httpx2.Client:
        return httpx2.Client(transport=httpx2.MockTransport(self))

    def client(self) -> AnkiConnectClient:
        return AnkiConnectClient(URL, http_client=self.http_client())

    def gateway(
        self, *, deck: str = DECK, note_types: Mapping[NoteKind, NoteTypeSpec] = NOTE_TYPES
    ) -> AnkiConnectGateway:
        return AnkiConnectGateway(self.client(), deck=deck, note_types=note_types)

    def note_infos(self) -> list[dict[str, object]]:
        """What `notesInfo` answers for every note, oldest first."""
        return [_note_info(note) for note in self.notes]

    @property
    def actions(self) -> list[str]:
        return [str(request["action"]) for request in self.requests]

    def params(self, action: str) -> list[dict[str, object]]:
        """The params of every request for this action, oldest first."""
        found = []
        for request in self.requests:
            if request["action"] == action:
                params = request["params"]
                assert isinstance(params, dict)
                found.append(params)
        return found

    # --- Transport ------------------------------------------------------------------------

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if self.down:
            raise httpx2.ConnectError("[Errno 111] Connection refused", request=request)
        body = json.loads(request.content)
        self.requests.append(body)
        action = body["action"]
        if action in self.errors:
            return _answer(None, self.errors[action])
        if action in self.results:
            return _answer(self.results[action], None)
        try:
            result = getattr(self, f"_{action}")(**body.get("params", {}))
        except ActionFailed as exc:
            return _answer(None, str(exc))
        return _answer(result, None)

    # --- Actions --------------------------------------------------------------------------

    def _version(self) -> int:
        return self.version

    def _deckNames(self) -> list[str]:
        return list(self.decks)

    def _createDeck(self, deck: str) -> int:
        if deck not in self.decks:
            self.decks.append(deck)
        return self.decks.index(deck) + 1

    def _modelNames(self) -> list[str]:
        return list(self.models)

    def _modelFieldNames(self, modelName: str) -> list[str]:
        return list(self._model(modelName).fields)

    def _createModel(
        self,
        modelName: str,
        inOrderFields: list[str],
        cardTemplates: list[dict[str, str]],
        css: str = "",
        isCloze: bool = False,
    ) -> dict[str, object]:
        if modelName in self.models:
            raise ActionFailed("Model name already exists")
        self.models[modelName] = Model(list(inOrderFields), css, list(cardTemplates))
        return {"name": modelName}

    def _findNotes(self, query: str) -> list[int]:
        match = _NOTE_QUERY.fullmatch(query)
        if match is None:
            raise ActionFailed(f"the mock understands only note: queries, got {query!r}")
        model = _ESCAPED.sub(r"\1", match.group(1))
        return [note.note_id for note in self.notes if note.model == model]

    def _notesInfo(self, notes: list[int]) -> list[dict[str, object]]:
        by_id = {note.note_id: note for note in self.notes}
        return [_note_info(by_id[note_id]) if note_id in by_id else {} for note_id in notes]

    def _addNote(self, note: dict[str, object]) -> int:
        deck, model_name = str(note["deckName"]), str(note["modelName"])
        if deck not in self.decks:
            raise ActionFailed(f"deck was not found: {deck}")
        model = self._model(model_name)
        given = note["fields"]
        assert isinstance(given, dict)
        fields = {name: str(given.get(name, "")) for name in model.fields}
        first = fields[model.fields[0]]
        if not first.strip():
            raise ActionFailed("cannot create note because it is empty")
        if any(n.model == model_name and n.fields[model.fields[0]] == first for n in self.notes):
            raise ActionFailed("cannot create note because it is a duplicate")
        tags = note.get("tags", [])
        assert isinstance(tags, list)
        self.notes.append(Note(len(self.notes) + 1, deck, model_name, fields, list(tags)))
        return self.notes[-1].note_id

    def _model(self, name: str) -> Model:
        if name not in self.models:
            raise ActionFailed(f"model was not found: {name}")
        return self.models[name]


def _note_info(note: Note) -> dict[str, object]:
    fields = {
        name: {"value": value, "order": order}
        for order, (name, value) in enumerate(note.fields.items())
    }
    return {
        "noteId": note.note_id,
        "modelName": note.model,
        "tags": note.tags,
        "fields": fields,
        "cards": [],
    }


def _answer(result: object, error: str | None) -> httpx2.Response:
    return httpx2.Response(200, json={"result": result, "error": error})

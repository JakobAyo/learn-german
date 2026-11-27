"""Anki adapter: the AnkiConnect client, the gateway and the tool's note types (0003)."""

from learn_german.adapters.anki.client import API_VERSION, AnkiConnectClient
from learn_german.adapters.anki.errors import AnkiActionError
from learn_german.adapters.anki.gateway import AnkiConnectGateway
from learn_german.adapters.anki.note_types import (
    NOTE_TYPES,
    TRANSFORMATION_V1,
    CardTemplate,
    NoteTypeSpec,
)

__all__ = [
    "API_VERSION",
    "NOTE_TYPES",
    "TRANSFORMATION_V1",
    "AnkiActionError",
    "AnkiConnectClient",
    "AnkiConnectGateway",
    "CardTemplate",
    "NoteTypeSpec",
]

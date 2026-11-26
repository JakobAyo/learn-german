"""The tool's Anki note types, `-v1` (0003, 0038, docs/learning-design/note-types.md).

Field names and order are part of the notes already in Anki: changing them needs a `-v2`
type and a migration, and a frozen test fails until both exist. Templates and CSS are
package files under `templates/`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from types import MappingProxyType
from typing import Final

from learn_german.domain.models import CHUNK_KEY_FIELD, NoteKind


@dataclass(frozen=True, slots=True)
class CardTemplate:
    """One card of a note type: its name and the front and back HTML."""

    name: str
    front: str
    back: str


@dataclass(frozen=True, slots=True)
class NoteTypeSpec:
    """What `ensure_setup` creates in Anki for one note kind.

    Raises ValueError unless `ChunkKey` is the first field, because Anki checks duplicates
    on the first field within a note type.
    """

    name: str
    note_kind: NoteKind
    fields: tuple[str, ...]
    templates: tuple[CardTemplate, ...]
    css: str

    def __post_init__(self) -> None:
        if not self.fields or self.fields[0] != CHUNK_KEY_FIELD:
            raise ValueError(f"note type {self.name!r} must start with {CHUNK_KEY_FIELD!r}")
        if len(set(self.fields)) != len(self.fields):
            raise ValueError(f"note type {self.name!r} has a field twice: {self.fields}")


def _template_file(name: str) -> str:
    return files(__package__ or __name__).joinpath("templates", name).read_text(encoding="utf-8")


def _card(name: str, stem: str) -> CardTemplate:
    return CardTemplate(
        name=name,
        front=_template_file(f"{stem}_front.html"),
        back=_template_file(f"{stem}_back.html"),
    )


_SHARED_FIELDS: Final = (CHUNK_KEY_FIELD, "Chunk", "Meaning", "Answer")
_CSS: Final = _template_file("style_v1.css")

TRANSFORMATION_V1: Final = NoteTypeSpec(
    name="learn-german-transformation-v1",
    note_kind=NoteKind.TRANSFORMATION,
    fields=(*_SHARED_FIELDS, "Prompt"),
    templates=(_card("Transformation", "transformation_v1"),),
    css=_CSS,
)

TRANSLATION_V1: Final = NoteTypeSpec(
    name="learn-german-translation-v1",
    note_kind=NoteKind.TRANSLATION,
    fields=(*_SHARED_FIELDS, "Prompt", "HintLanguage"),
    templates=(_card("Translation", "translation_v1"),),
    css=_CSS,
)

NOTE_TYPES: Final[Mapping[NoteKind, NoteTypeSpec]] = MappingProxyType(
    {spec.note_kind: spec for spec in (TRANSFORMATION_V1, TRANSLATION_V1)}
)
"""The current note type of each note kind."""

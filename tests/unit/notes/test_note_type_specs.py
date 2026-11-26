"""The v1 note types: frozen fields, agreement with the builder, and golden card rendering.

The field lists are asserted literally on purpose (0003, 0038). If this test fails because
a field changed, create a `-v2` note type and a migration instead of editing the test.

When a template or the sample content changes on purpose, update the golden file in
tests/data/anki/ by hand and check the cards in Anki (docs/integrations/ankiconnect.md).
"""

import re
from pathlib import Path

import pytest

from learn_german.adapters.anki import (
    NOTE_TYPES,
    TRANSFORMATION_V1,
    TRANSLATION_V1,
    CardTemplate,
    NoteTypeSpec,
)
from learn_german.application.notes import NoteBuilder
from learn_german.domain.models import NoteKind
from tests.unit.notes.samples import CONTENT, REQUEST, RUN

DATA = Path(__file__).parents[2] / "data" / "anki"
_FIELD_REFERENCE = re.compile(r"\{\{([^{}]+)\}\}")


def test_transformation_v1_fields_are_frozen() -> None:
    assert TRANSFORMATION_V1.name == "learn-german-transformation-v1"
    assert TRANSFORMATION_V1.fields == ("ChunkKey", "Chunk", "Meaning", "Answer", "Prompt")


def test_translation_v1_fields_are_frozen() -> None:
    assert TRANSLATION_V1.name == "learn-german-translation-v1"
    assert TRANSLATION_V1.fields == (
        "ChunkKey",
        "Chunk",
        "Meaning",
        "Answer",
        "Prompt",
        "HintLanguage",
    )


def test_every_note_kind_has_a_note_type() -> None:
    assert {kind: spec.note_kind for kind, spec in NOTE_TYPES.items()} == {
        kind: kind for kind in NoteKind
    }


@pytest.mark.parametrize("kind", list(NoteKind), ids=str)
def test_builder_fields_match_the_note_type(kind: NoteKind) -> None:
    builder = NoteBuilder.for_run(provider="anthropic", model="claude-opus-5-5", run_id=RUN)

    (draft,) = builder.build(REQUEST, CONTENT, [kind])

    assert tuple(name for name, _ in draft.fields) == NOTE_TYPES[kind].fields


@pytest.mark.parametrize("spec", list(NOTE_TYPES.values()), ids=lambda spec: spec.name)
def test_templates_use_only_their_note_types_fields(spec: NoteTypeSpec) -> None:
    for card in spec.templates:
        used = set(_FIELD_REFERENCE.findall(card.front + card.back))

        assert used <= {*spec.fields, "FrontSide"}
        assert "ChunkKey" not in used


@pytest.mark.parametrize("spec", list(NOTE_TYPES.values()), ids=lambda spec: spec.name)
def test_cards_render_as_the_golden_file(spec: NoteTypeSpec) -> None:
    builder = NoteBuilder.for_run(provider="anthropic", model="claude-opus-5-5", run_id=RUN)
    (draft,) = builder.build(REQUEST, CONTENT, [spec.note_kind])
    (card,) = spec.templates
    golden = DATA / f"{spec.note_kind}_v1.golden.html"

    assert render(card, dict(draft.fields)) == golden.read_text(encoding="utf-8")


def test_note_type_spec_needs_the_chunk_key_first() -> None:
    with pytest.raises(ValueError, match="must start with 'ChunkKey'"):
        NoteTypeSpec("t", NoteKind.TRANSFORMATION, ("Chunk", "ChunkKey"), (), "")


def test_note_type_spec_rejects_a_repeated_field() -> None:
    with pytest.raises(ValueError, match="has a field twice"):
        NoteTypeSpec("t", NoteKind.TRANSFORMATION, ("ChunkKey", "Chunk", "Chunk"), (), "")


def render(card: CardTemplate, fields: dict[str, str]) -> str:
    """Front and back the way Anki fills plain `{{Field}}` references and `{{FrontSide}}`."""
    front = _fill(card.front, fields)
    back = _fill(card.back, {**fields, "FrontSide": front})
    return f"<!-- {card.name} front -->\n{front}<!-- {card.name} back -->\n{back}"


def _fill(template: str, fields: dict[str, str]) -> str:
    return _FIELD_REFERENCE.sub(lambda match: fields[match.group(1)], template)

"""NoteBuilder: card content to the note of a chunk (0012, 0028, 0049, note-types.md)."""

import pytest

from learn_german.application.notes import NoteBuilder
from learn_german.domain.models import NoteKind
from tests.unit.notes.samples import CONTENT, DECISION, REQUEST, RUN

TAGS = (
    "learn-german",
    "provider::anthropic",
    "model::claude-opus-5-5",
    "run::run-20261124-1530",
)


@pytest.fixture
def builder() -> NoteBuilder:
    return NoteBuilder.for_run(provider="anthropic", model="claude-opus-5-5", run_id=RUN)


def test_builder_makes_one_transformation_note_by_default(builder: NoteBuilder) -> None:
    drafts = builder.build(REQUEST, CONTENT)

    assert [draft.note_kind for draft in drafts] == [NoteKind.TRANSFORMATION]
    assert {draft.key for draft in drafts} == {DECISION}


def test_builder_fills_the_transformation_fields(builder: NoteBuilder) -> None:
    (draft,) = builder.build(REQUEST, CONTENT, [NoteKind.TRANSFORMATION])

    assert draft.fields == (
        ("ChunkKey", "entscheidung|treffen"),
        ("Chunk", "eine Entscheidung treffen"),
        ("Meaning", "eine Entscheidung treffen = entscheiden, sich festlegen"),
        ("Answer", "Der Stadtrat hat am Montag eine Entscheidung über die Brücke getroffen."),
        ("Prompt", "Der Stadtrat hat am Montag über die Brücke entschieden."),
    )


def test_builder_tags_every_note_with_the_run(builder: NoteBuilder) -> None:
    drafts = builder.build(REQUEST, CONTENT)

    assert [draft.tags for draft in drafts] == [TAGS]


def test_builder_builds_only_the_kinds_asked_for(builder: NoteBuilder) -> None:
    assert [d.note_kind for d in builder.build(REQUEST, CONTENT, [NoteKind.TRANSFORMATION])] == [
        NoteKind.TRANSFORMATION
    ]
    assert builder.build(REQUEST, CONTENT, []) == ()

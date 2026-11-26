"""NoteBuilder: card content to the two notes of a chunk (0012, 0028, note-types.md)."""

from dataclasses import replace

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


def test_builder_makes_one_note_of_each_kind_by_default(builder: NoteBuilder) -> None:
    drafts = builder.build(REQUEST, CONTENT)

    assert [draft.note_kind for draft in drafts] == [NoteKind.TRANSFORMATION, NoteKind.TRANSLATION]
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


def test_builder_fills_the_translation_fields(builder: NoteBuilder) -> None:
    (draft,) = builder.build(REQUEST, CONTENT, [NoteKind.TRANSLATION])

    assert draft.fields == (
        ("ChunkKey", "entscheidung|treffen"),
        ("Chunk", "eine Entscheidung treffen"),
        ("Meaning", "eine Entscheidung treffen = entscheiden, sich festlegen"),
        ("Answer", "Der Stadtrat hat am Montag eine Entscheidung über die Brücke getroffen."),
        ("Prompt", "The city council made a decision about the bridge on Monday."),
        ("HintLanguage", "en"),
    )


def test_builder_records_the_requests_hint_language(builder: NoteBuilder) -> None:
    (draft,) = builder.build(replace(REQUEST, hint_language="fr"), CONTENT, [NoteKind.TRANSLATION])

    assert dict(draft.fields)["HintLanguage"] == "fr"


def test_builder_tags_every_note_with_the_run(builder: NoteBuilder) -> None:
    drafts = builder.build(REQUEST, CONTENT)

    assert [draft.tags for draft in drafts] == [TAGS, TAGS]


def test_builder_builds_only_the_kinds_asked_for(builder: NoteBuilder) -> None:
    assert [d.note_kind for d in builder.build(REQUEST, CONTENT, [NoteKind.TRANSLATION])] == [
        NoteKind.TRANSLATION
    ]
    assert builder.build(REQUEST, CONTENT, []) == ()

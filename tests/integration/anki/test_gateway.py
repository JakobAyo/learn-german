"""AnkiConnectGateway over a mocked AnkiConnect: the requests it sends and how it fails.

Behaviour it shares with the fake is in tests/contract/test_anki_gateway.py.
"""

from dataclasses import replace

import pytest

from learn_german.adapters.anki import (
    NOTE_TYPES,
    TRANSFORMATION_V1,
    TRANSLATION_V1,
    AnkiActionError,
    NoteTypeSpec,
)
from learn_german.application.notes import NoteBuilder
from learn_german.domain.errors import (
    AnkiUnavailableError,
    FatalError,
    ItemError,
    NoteTypeMismatchError,
    PushError,
)
from learn_german.domain.models import NoteDraft, NoteKind
from tests.integration.anki.mock_ankiconnect import DECK, MockAnkiConnect
from tests.unit.notes.samples import CONTENT, DECISION, DISPOSAL, REQUEST, RUN

TRANSFORMATION = NoteKind.TRANSFORMATION
TRANSLATION = NoteKind.TRANSLATION
BUILDER = NoteBuilder.for_run(provider="anthropic", model="claude-opus-5-5", run_id=RUN)


@pytest.fixture
def anki() -> MockAnkiConnect:
    return MockAnkiConnect()


def drafts(*kinds: NoteKind) -> tuple[NoteDraft, ...]:
    return BUILDER.build(REQUEST, CONTENT, kinds or tuple(NoteKind))


# --- ensure_setup ----------------------------------------------------------------------------


def test_setup_creates_the_deck_and_both_note_types(anki: MockAnkiConnect) -> None:
    anki.gateway().ensure_setup()

    assert anki.actions == [
        "version",
        "deckNames",
        "createDeck",
        "modelNames",
        "createModel",
        "createModel",
    ]
    assert anki.params("createDeck") == [{"deck": DECK}]
    assert DECK in anki.decks


@pytest.mark.parametrize("spec", [TRANSFORMATION_V1, TRANSLATION_V1], ids=lambda s: s.name)
def test_setup_creates_a_note_type_from_its_spec(anki: MockAnkiConnect, spec: NoteTypeSpec) -> None:
    anki.gateway().ensure_setup()

    (sent,) = [p for p in anki.params("createModel") if p["modelName"] == spec.name]
    assert sent == {
        "modelName": spec.name,
        "inOrderFields": list(spec.fields),
        "css": spec.css,
        "isCloze": False,
        "cardTemplates": [
            {"Name": card.name, "Front": card.front, "Back": card.back} for card in spec.templates
        ],
    }


def test_setup_a_second_time_creates_nothing(anki: MockAnkiConnect) -> None:
    gateway = anki.gateway()
    gateway.ensure_setup()
    anki.requests.clear()

    gateway.ensure_setup()

    assert anki.actions == [
        "version",
        "deckNames",
        "modelNames",
        "modelFieldNames",
        "modelFieldNames",
    ]


def test_setup_leaves_an_existing_note_types_templates_and_styling_alone(
    anki: MockAnkiConnect,
) -> None:
    anki.decks.append(DECK)
    for spec in NOTE_TYPES.values():
        anki.add_model(spec.name, spec.fields, css=".card { color: hotpink; }")

    anki.gateway().ensure_setup()

    assert not {"createDeck", "createModel"} & set(anki.actions)
    assert {model.css for model in anki.models.values()} == {".card { color: hotpink; }"}


def test_setup_fails_fatally_when_a_note_types_fields_differ(anki: MockAnkiConnect) -> None:
    anki.add_model(TRANSLATION_V1.name, ["ChunkKey", "Chunk", "Meaning", "Answer", "Prompt"])

    with pytest.raises(NoteTypeMismatchError) as caught:
        anki.gateway().ensure_setup()

    message = str(caught.value)
    assert isinstance(caught.value, FatalError)
    assert TRANSLATION_V1.name in message
    assert "ChunkKey, Chunk, Meaning, Answer, Prompt, HintLanguage in that order" in message


def test_setup_fails_on_reordered_fields(anki: MockAnkiConnect) -> None:
    anki.add_model(TRANSFORMATION_V1.name, ["ChunkKey", "Chunk", "Meaning", "Prompt", "Answer"])

    with pytest.raises(NoteTypeMismatchError):
        anki.gateway().ensure_setup()


def test_setup_stops_before_any_change_when_ankiconnect_is_too_old() -> None:
    anki = MockAnkiConnect(version=5)

    with pytest.raises(AnkiUnavailableError, match="Update the add-on"):
        anki.gateway().ensure_setup()

    assert anki.actions == ["version"]


def test_setup_fails_on_a_malformed_answer(anki: MockAnkiConnect) -> None:
    anki.results["deckNames"] = {"Default": 1}

    with pytest.raises(AnkiActionError, match="deckNames"):
        anki.gateway().ensure_setup()


# --- existing_keys ---------------------------------------------------------------------------


def test_existing_keys_search_the_note_type_across_the_collection(anki: MockAnkiConnect) -> None:
    anki.add_existing(TRANSFORMATION, DECISION, deck="Default")

    keys = anki.gateway().existing_keys(TRANSFORMATION)

    assert keys == {DECISION}
    assert anki.params("findNotes") == [{"query": '"note:learn-german-transformation-v1"'}]


def test_existing_keys_skip_note_info_when_there_are_no_notes(anki: MockAnkiConnect) -> None:
    assert anki.gateway().existing_keys(TRANSLATION) == frozenset()
    assert anki.actions == ["findNotes"]


def test_existing_keys_skip_notes_without_a_valid_key(anki: MockAnkiConnect) -> None:
    name = TRANSFORMATION_V1.name
    anki.add_note(name, {"ChunkKey": " entscheidung|treffen "})
    anki.add_note(name, {"ChunkKey": "Eine Entscheidung"})
    anki.add_note(name, {"Chunk": "zur Verfügung stellen"})
    anki.results["notesInfo"] = [*anki.note_infos(), {}, "not a note"]

    assert anki.gateway().existing_keys(TRANSFORMATION) == {DECISION}


@pytest.mark.parametrize("action", ["findNotes", "notesInfo"])
def test_existing_keys_fail_on_a_malformed_answer(anki: MockAnkiConnect, action: str) -> None:
    anki.add_existing(TRANSFORMATION, DECISION)
    anki.results[action] = "oops"

    with pytest.raises(AnkiActionError, match=action):
        anki.gateway().existing_keys(TRANSFORMATION)


def test_existing_keys_escape_search_syntax_in_the_note_type_name(anki: MockAnkiConnect) -> None:
    odd = replace(TRANSFORMATION_V1, name='my_type "*" \\ v1')
    anki.add_note(odd.name, {"ChunkKey": DECISION.value})

    keys = anki.gateway(note_types={TRANSFORMATION: odd}).existing_keys(TRANSFORMATION)

    assert keys == {DECISION}
    assert anki.params("findNotes") == [{"query": '"note:my\\_type \\"\\*\\" \\\\ v1"'}]


# --- add_notes -------------------------------------------------------------------------------


def test_add_notes_sends_one_add_note_per_draft(anki: MockAnkiConnect) -> None:
    gateway = anki.gateway()
    gateway.ensure_setup()
    anki.requests.clear()

    gateway.add_notes(drafts())

    assert anki.actions == ["addNote", "addNote"]
    transformation, translation = (p["note"] for p in anki.params("addNote"))
    assert transformation == {
        "deckName": DECK,
        "modelName": "learn-german-transformation-v1",
        "fields": dict(drafts(TRANSFORMATION)[0].fields),
        "tags": [
            "learn-german",
            "provider::anthropic",
            "model::claude-opus-5-5",
            "run::run-20261124-1530",
        ],
        "options": {"allowDuplicate": False, "duplicateScope": "collection"},
    }
    assert isinstance(translation, dict)
    assert translation["modelName"] == "learn-german-translation-v1"


def test_add_notes_escape_html_in_field_values(anki: MockAnkiConnect) -> None:
    gateway = anki.gateway()
    gateway.ensure_setup()
    content = replace(CONTENT, meaning="eine Entscheidung treffen = <entscheiden> & festlegen")

    gateway.add_notes(BUILDER.build(REQUEST, content, [TRANSFORMATION]))

    (note,) = anki.notes
    assert (
        note.fields["Meaning"] == "eine Entscheidung treffen = &lt;entscheiden&gt; &amp; festlegen"
    )


def test_add_notes_turn_a_rejection_into_a_push_error(anki: MockAnkiConnect) -> None:
    gateway = anki.gateway()
    gateway.ensure_setup()
    anki.errors["addNote"] = "cannot create note because it is empty"

    with pytest.raises(PushError) as caught:
        gateway.add_notes(drafts(TRANSLATION))

    assert isinstance(caught.value, ItemError)
    assert "translation note for entscheidung|treffen" in str(caught.value)
    assert "cannot create note because it is empty" in str(caught.value)


def test_add_notes_refuse_a_draft_whose_fields_are_not_its_note_types(
    anki: MockAnkiConnect,
) -> None:
    (draft,) = drafts(TRANSFORMATION)
    wrong = replace(draft, note_kind=TRANSLATION)

    with pytest.raises(ValueError, match="has the fields"):
        anki.gateway().add_notes([wrong])

    assert anki.requests == []


def test_add_notes_stop_fatally_when_anki_goes_away(anki: MockAnkiConnect) -> None:
    gateway = anki.gateway()
    gateway.ensure_setup()
    anki.down = True

    with pytest.raises(AnkiUnavailableError):
        gateway.add_notes(drafts(TRANSFORMATION))


def test_notes_of_other_keys_and_kinds_do_not_count(anki: MockAnkiConnect) -> None:
    anki.add_existing(TRANSLATION, DISPOSAL)

    assert anki.gateway().existing_keys(TRANSFORMATION) == frozenset()

"""The LLM output schema: what is sent to the API and how answers are validated."""

import json

import pytest

from learn_german.adapters.llm.schema import CARD_SCHEMA, parse_card
from learn_german.domain.errors import GenerationError
from learn_german.domain.models import CardContent
from tests.unit.generation.builders import CONTENT, DECISION

FIELDS = ["citation_form", "shortened_sentence", "verbal_rewrite", "translation", "meaning"]


def _answer(**changes: object) -> str:
    data: dict[str, object] = {name: getattr(CONTENT, name) for name in FIELDS}
    data.update(changes)
    return json.dumps({name: value for name, value in data.items() if value is not None})


def test_schema_requires_every_content_field_and_nothing_else() -> None:
    assert CARD_SCHEMA["type"] == "object"
    assert CARD_SCHEMA["required"] == FIELDS
    assert CARD_SCHEMA["additionalProperties"] is False
    properties = CARD_SCHEMA["properties"]
    assert isinstance(properties, dict)
    assert list(properties) == FIELDS


def test_schema_fields_match_card_content() -> None:
    assert list(CardContent.__dataclass_fields__) == FIELDS


def test_valid_answer_becomes_card_content() -> None:
    assert parse_card(_answer(), DECISION) == CONTENT


def test_values_are_stripped() -> None:
    card = parse_card(_answer(meaning="  eine Entscheidung treffen = entscheiden \n"), DECISION)

    assert card.meaning == "eine Entscheidung treffen = entscheiden"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param('{"citation_form": "eine Entscheidung', id="truncated-json"),
        pytest.param("Hier ist die Karte.", id="prose"),
        pytest.param(_answer(meaning=None), id="missing-field"),
        pytest.param(_answer(extra="x"), id="extra-field"),
        pytest.param(_answer(translation="   "), id="blank-field"),
        pytest.param(_answer(translation=3), id="wrong-type"),
        pytest.param("[]", id="not-an-object"),
    ],
)
def test_invalid_answer_raises_generation_error(text: str) -> None:
    with pytest.raises(GenerationError, match=r"entscheidung\|treffen"):
        parse_card(text, DECISION)

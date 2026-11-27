"""The structured output an LLM returns for one chunk, validated at the adapter boundary."""

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from learn_german.domain.errors import GenerationError
from learn_german.domain.models import CardContent, ChunkKey


class CardOutput(BaseModel):
    """One field per `CardContent` field. Values are stripped and must not be empty."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    citation_form: str = Field(min_length=1, description="The chunk in dictionary form.")
    shortened_sentence: str = Field(
        min_length=1, description="The source sentence shortened to the clause around the chunk."
    )
    verbal_rewrite: str = Field(
        min_length=1, description="shortened_sentence with the chunk replaced by a verb."
    )
    meaning: str = Field(min_length=1, description="One-line German explanation of the chunk.")

    def to_content(self) -> CardContent:
        return CardContent(
            citation_form=self.citation_form,
            shortened_sentence=self.shortened_sentence,
            verbal_rewrite=self.verbal_rewrite,
            meaning=self.meaning,
        )


def _json_schema() -> dict[str, object]:
    # Built by hand from the model's fields rather than with model_json_schema(), so only
    # keywords that structured outputs accept are sent; length rules are checked locally.
    properties: dict[str, object] = {
        name: {"type": "string", "description": field.description}
        for name, field in CardOutput.model_fields.items()
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(CardOutput.model_fields),
        "additionalProperties": False,
    }


CARD_SCHEMA: Final = _json_schema()
"""JSON schema sent to the LLM as the required output format."""


def parse_card(text: str, key: ChunkKey) -> CardContent:
    """Validate the LLM's JSON text. Raises `GenerationError` if it is not valid JSON or does
    not match the schema."""
    try:
        return CardOutput.model_validate_json(text).to_content()
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'output'}: {error['msg']}"
            for error in exc.errors()
        )
        raise GenerationError(
            f"The LLM's answer for {key} is not valid card content ({problems}). "
            "The chunk stays pending, and the next sync asks again."
        ) from exc

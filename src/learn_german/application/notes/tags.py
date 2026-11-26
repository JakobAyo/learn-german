"""Tags that make every note of a run findable in Anki (R22, 0005)."""

import re
from typing import Final

from learn_german.domain.models import RunId

TOOL_TAG: Final = "learn-german"

_WHITESPACE = re.compile(r"\s+")


def run_tags(*, provider: str, model: str, run_id: RunId) -> tuple[str, ...]:
    """`learn-german`, `provider::<name>`, `model::<id>` and `run::<run-id>`, in that order.

    Anki splits tags on whitespace, so whitespace inside a name becomes `_`.
    Raises ValueError if the provider or model is blank.
    """
    return (
        TOOL_TAG,
        f"provider::{_tag_value(provider, 'provider')}",
        f"model::{_tag_value(model, 'model')}",
        f"run::{run_id}",
    )


def _tag_value(value: str, what: str) -> str:
    cleaned = _WHITESPACE.sub("_", value.strip())
    if not cleaned:
        raise ValueError(f"{what} for a tag must not be blank")
    return cleaned

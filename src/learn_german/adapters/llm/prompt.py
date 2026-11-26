"""The card prompt: a template file plus `PROMPT_VERSION` (0035).

The template is shared by every LLM adapter in this package. Rendering is a pure function of
the template and the request. Changing the template without bumping `PROMPT_VERSION` would
serve stale cache entries, so a test pins the template's hash per version.
"""

from importlib.resources import files
from string import Template
from typing import Final

from learn_german.domain.models import CardRequest

PROMPT_VERSION: Final = "card-v1"
"""Part of every cache key (0004). Bump it, and add a template file, for any prompt change."""

_TEMPLATE_FILES: Final = {"card-v1": "card_v1.md"}
_NO_CONTEXT: Final = "(none)"


def load_template(version: str = PROMPT_VERSION) -> str:
    """The template text of a prompt version. Raises KeyError for an unknown version."""
    folder = files(__package__ or __name__).joinpath("prompts")
    return folder.joinpath(_TEMPLATE_FILES[version]).read_text(encoding="utf-8")


def render_prompt(template: str, request: CardRequest) -> str:
    """The user message for one chunk. Raises KeyError if the template has an unknown field."""
    return Template(template).substitute(
        key=request.key.value,
        sentence=request.sentence.strip(),
        context=request.context.strip() or _NO_CONTEXT,
        hint_language=request.hint_language,
    )

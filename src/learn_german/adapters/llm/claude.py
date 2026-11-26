"""`AnthropicProvider`: card content from the Claude API (0004, 0037)."""

import logging
from typing import Final, Literal, Self

import anthropic
import httpx2
from anthropic.types import Message

from learn_german.adapters.llm.errors import LLMAccessError, LLMRequestError
from learn_german.adapters.llm.prompt import PROMPT_VERSION, load_template, render_prompt
from learn_german.adapters.llm.schema import CARD_SCHEMA, parse_card
from learn_german.domain.errors import GenerationError, MissingCredentialsError
from learn_german.domain.models import CardContent, CardRequest

logger = logging.getLogger(__name__)

PROVIDER_NAME: Final = "anthropic"
DEFAULT_MODEL: Final = "claude-opus-5-5"
DEFAULT_EFFORT: Final = "medium"
DEFAULT_MAX_TOKENS: Final = 16_000
DEFAULT_MAX_RETRIES: Final = 2

Effort = Literal["low", "medium", "high", "xhigh", "max"]

# Errors after which every further call fails too, so the run stops (0014, 0037). Spend
# limits arrive as 429 like rate limits but do not pass by waiting.
_FATAL_ERRORS: Final = (
    anthropic.BadRequestError,
    anthropic.AuthenticationError,
    anthropic.PaymentRequiredError,
    anthropic.PermissionDeniedError,
    anthropic.NotFoundError,
    anthropic.EnforcedSpendLimitReachedError,
    anthropic.ContractSpendLimitReachedError,
)


class AnthropicProvider:
    """Implements `ports.LLMProvider` with the Anthropic SDK.

    One Messages call per chunk, with the rendered card prompt as the user message and the
    `CardOutput` JSON schema as the required output format. The SDK retries rate limits,
    server errors and network errors itself (`max_retries`).

    Raises `LLMAccessError` (fatal) when the API rejects the request, key, account or
    model, `LLMRequestError` when the call still fails after retries, and `GenerationError`
    when the answer is refused, cut off, or not valid card content.
    """

    def __init__(
        self,
        client: anthropic.Anthropic,
        *,
        model: str = DEFAULT_MODEL,
        effort: Effort = DEFAULT_EFFORT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        template: str | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._effort: Effort = effort
        self._max_tokens = max_tokens
        self._template = load_template() if template is None else template

    @classmethod
    def create(
        cls,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        effort: Effort = DEFAULT_EFFORT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx2.Client | None = None,
    ) -> Self:
        """A provider with its own SDK client. Tests pass an `http_client` with a mock transport.

        Raises `MissingCredentialsError` if the API key is empty.
        """
        if not api_key:
            raise MissingCredentialsError(
                "ANTHROPIC_API_KEY is empty. Create a key in the Claude Console "
                "(platform.claude.com), then export it or put it in a .env file in the "
                "directory you run learn-german from."
            )
        client = anthropic.Anthropic(
            api_key=api_key, max_retries=max_retries, http_client=http_client
        )
        return cls(client, model=model, effort=effort)

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def model(self) -> str:
        return self._model

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION

    def generate(self, request: CardRequest) -> CardContent:
        prompt = render_prompt(self._template, request)
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "effort": self._effort,
                    "format": {"type": "json_schema", "schema": CARD_SCHEMA},
                },
            )
        except _FATAL_ERRORS as exc:
            raise LLMAccessError(_access_message(exc, self._model)) from exc
        except anthropic.APIError as exc:
            raise LLMRequestError(
                f"The Claude API call for {request.key} failed after retries: {exc}. "
                "The chunk stays pending; run sync again later."
            ) from exc
        logger.debug(
            "Claude answered for %s: request %s, %s input and %s output tokens",
            request.key,
            message._request_id,
            message.usage.input_tokens,
            message.usage.output_tokens,
        )
        return parse_card(_answer_text(message, request), request.key)


def _access_message(exc: anthropic.APIStatusError, model: str) -> str:
    detail = f"(HTTP {exc.status_code}: {exc.message})"
    if isinstance(exc, anthropic.AuthenticationError):
        return f"The Claude API rejected the API key {detail}. Check ANTHROPIC_API_KEY."
    if isinstance(exc, anthropic.NotFoundError):
        return (
            f"The Claude API does not know the model {model!r} {detail}. "
            "Set a valid model ID with LEARN_GERMAN_MODEL or model in config.toml."
        )
    if isinstance(exc, anthropic.BadRequestError):
        return (
            f"The Claude API refused the request for model {model!r} {detail}. Check that "
            "the model supports structured outputs and effort, and that the account is active."
        )
    return (
        f"The Claude API refused access {detail}. Check the account's credit, spend limits "
        "and the API key's permissions in the Claude Console."
    )


def _answer_text(message: Message, request: CardRequest) -> str:
    if message.stop_reason == "refusal":
        raise GenerationError(
            f"Claude declined to write cards for {request.key}. The chunk stays pending, and "
            "the next sync asks again; if Claude keeps declining, the chunk just keeps "
            "failing and nothing else is affected."
        )
    if message.stop_reason == "max_tokens":
        raise GenerationError(
            f"Claude's answer for {request.key} was cut off at the token limit. "
            "The chunk stays pending, and the next sync asks again."
        )
    text = "".join(block.text for block in message.content if block.type == "text")
    if not text.strip():
        raise GenerationError(
            f"Claude's answer for {request.key} has no text (stop reason "
            f"{message.stop_reason}). The chunk stays pending, and the next sync asks again."
        )
    return text

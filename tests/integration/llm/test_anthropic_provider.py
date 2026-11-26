"""AnthropicProvider against a mocked Messages API (httpx2.MockTransport, 0027, 0037)."""

import json

import httpx2
import pytest

from learn_german.adapters.llm import (
    PROMPT_VERSION,
    AnthropicProvider,
    LLMAccessError,
    LLMRequestError,
    load_template,
    render_prompt,
)
from learn_german.adapters.llm.schema import CARD_SCHEMA
from learn_german.domain.errors import (
    FatalError,
    GenerationError,
    ItemError,
    MissingCredentialsError,
)
from learn_german.domain.models import CardContent
from learn_german.ports import LLMProvider
from tests.integration.llm.mock_api import ScriptedApi, error, message
from tests.unit.generation.builders import CONTENT, REQUEST

ANSWER = json.dumps(
    {
        "citation_form": CONTENT.citation_form,
        "shortened_sentence": CONTENT.shortened_sentence,
        "verbal_rewrite": CONTENT.verbal_rewrite,
        "translation": CONTENT.translation,
        "meaning": CONTENT.meaning,
    },
    ensure_ascii=False,
)


def test_success_returns_card_content() -> None:
    api = ScriptedApi([message(ANSWER)])

    assert api.provider().generate(REQUEST) == CONTENT


def test_request_carries_model_prompt_schema_and_effort() -> None:
    api = ScriptedApi([message(ANSWER)])

    api.provider(model="claude-haiku-5-5", effort="low").generate(REQUEST)

    request = api.requests[0]
    body = api.body()
    assert request.url.path == "/v1/messages"
    assert request.headers["authorization"] == "Bearer test-key"
    assert body["model"] == "claude-haiku-5-5"
    assert body["messages"] == [
        {"role": "user", "content": render_prompt(load_template(), REQUEST)}
    ]
    assert body["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": CARD_SCHEMA},
    }
    assert "thinking" not in body


def test_defaults_are_opus_at_medium_effort() -> None:
    api = ScriptedApi([message(ANSWER)])
    provider: LLMProvider = api.provider()

    provider.generate(REQUEST)

    assert (provider.name, provider.model, provider.prompt_version) == (
        "anthropic",
        "claude-opus-5-5",
        PROMPT_VERSION,
    )
    assert api.body()["model"] == "claude-opus-5-5"
    assert api.body()["output_config"]["effort"] == "medium"  # type: ignore[index]


def test_thinking_blocks_are_skipped() -> None:
    api = ScriptedApi([message(ANSWER, thinking=True)])

    assert api.provider().generate(REQUEST) == CONTENT


@pytest.mark.parametrize(
    "text",
    [
        pytest.param('{"citation_form": "eine Entscheidung treffen", ', id="malformed-json"),
        pytest.param(json.dumps({"citation_form": "eine Entscheidung treffen"}), id="missing"),
        pytest.param(ANSWER[:-1] + ', "note": "x"}', id="extra-field"),
        pytest.param("   ", id="empty-text"),
    ],
)
def test_unusable_answer_is_a_generation_error(text: str) -> None:
    api = ScriptedApi([message(text)])

    with pytest.raises(GenerationError):
        api.provider().generate(REQUEST)


@pytest.mark.parametrize(
    ("stop_reason", "fragment"),
    [
        pytest.param("refusal", "declined", id="refusal"),
        pytest.param("max_tokens", "cut off", id="max-tokens"),
    ],
)
def test_incomplete_answer_is_a_generation_error(stop_reason: str, fragment: str) -> None:
    api = ScriptedApi([message(ANSWER, stop_reason=stop_reason)])

    with pytest.raises(GenerationError, match=fragment):
        api.provider().generate(REQUEST)


@pytest.mark.parametrize(
    ("status", "error_type", "fragment"),
    [
        pytest.param(401, "authentication_error", "API key", id="401"),
        pytest.param(403, "permission_error", "refused access", id="403"),
        pytest.param(404, "not_found_error", "does not know the model", id="404"),
        pytest.param(400, "invalid_request_error", "refused the request", id="400"),
        pytest.param(402, "billing_error", "refused access", id="402"),
    ],
)
def test_access_errors_are_fatal_and_not_retried(
    status: int, error_type: str, fragment: str
) -> None:
    api = ScriptedApi([error(status, error_type)])

    with pytest.raises(LLMAccessError, match=fragment) as raised:
        api.provider().generate(REQUEST)

    assert isinstance(raised.value, FatalError)
    assert len(api.requests) == 1


def test_spend_limit_is_fatal_although_it_is_a_429() -> None:
    api = ScriptedApi([error(429, "rate_limit_error", code="enforced_spend_limit_reached")])

    with pytest.raises(LLMAccessError):
        api.provider(max_retries=0).generate(REQUEST)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        pytest.param(500, "api_error", id="500"),
        pytest.param(529, "overloaded_error", id="529"),
        pytest.param(429, "rate_limit_error", id="429"),
    ],
)
def test_server_errors_are_item_errors_after_retries(status: int, error_type: str) -> None:
    api = ScriptedApi([error(status, error_type)])

    with pytest.raises(LLMRequestError) as raised:
        api.provider(max_retries=2).generate(REQUEST)

    assert isinstance(raised.value, ItemError)
    assert len(api.requests) == 3


def test_a_retry_that_succeeds_returns_the_content() -> None:
    api = ScriptedApi([error(529, "overloaded_error"), message(ANSWER)])

    assert api.provider(max_retries=2).generate(REQUEST) == CONTENT
    assert len(api.requests) == 2


def test_network_error_is_an_item_error() -> None:
    api = ScriptedApi([httpx2.ConnectError("connection refused")])

    with pytest.raises(LLMRequestError):
        api.provider(max_retries=0).generate(REQUEST)


def test_empty_api_key_is_missing_credentials() -> None:
    with pytest.raises(MissingCredentialsError):
        AnthropicProvider.create("")


def test_custom_template_is_rendered() -> None:
    api = ScriptedApi([message(ANSWER)])
    template = "Satz: $sentence ($hint_language, $key, $context)"
    provider = AnthropicProvider(api.client(), template=template)

    result: CardContent = provider.generate(REQUEST)

    assert result == CONTENT
    assert api.body()["messages"][0]["content"].startswith("Satz: Nach einer")  # type: ignore[index]

"""A scripted stand-in for the Messages API behind `httpx2.MockTransport`. No network."""

import json
from collections.abc import Iterable

import anthropic
import httpx2

from learn_german.adapters.llm import AnthropicProvider
from learn_german.adapters.llm.claude import DEFAULT_EFFORT, DEFAULT_MODEL, Effort

Reply = httpx2.Response | Exception


def message(text: str, *, stop_reason: str = "end_turn", thinking: bool = False) -> httpx2.Response:
    """A Messages API success with one text block, optionally after a thinking block."""
    content: list[dict[str, object]] = [{"type": "text", "text": text}]
    if thinking:
        content.insert(0, {"type": "thinking", "thinking": "", "signature": "sig"})
    body = {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 900, "output_tokens": 120},
    }
    return httpx2.Response(200, json=body, headers={"request-id": "req_01"})


def error(status: int, error_type: str, *, code: str | None = None) -> httpx2.Response:
    """An API error, with `code` as its detailed error code if given.

    `retry-after-ms` keeps the SDK's retries from sleeping in tests.
    """
    detail: dict[str, object] = {"type": error_type, "message": "scripted error"}
    if code is not None:
        detail["details"] = {"error_code": code}
    body = {"type": "error", "error": detail}
    return httpx2.Response(status, json=body, headers={"retry-after-ms": "1"})


class ScriptedApi:
    """Answers each request with the next scripted reply and records every request.

    The last reply repeats once the script runs out, so a retried failure keeps failing.
    """

    def __init__(self, replies: Iterable[Reply]) -> None:
        self._replies = list(replies)
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        reply = self._replies[min(len(self.requests), len(self._replies)) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply

    def body(self, index: int = 0) -> dict[str, object]:
        data: dict[str, object] = json.loads(self.requests[index].content)
        return data

    def http_client(self) -> httpx2.Client:
        return httpx2.Client(transport=httpx2.MockTransport(self))

    def client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key="test-key", http_client=self.http_client())

    def provider(
        self, *, model: str = DEFAULT_MODEL, effort: Effort = DEFAULT_EFFORT, max_retries: int = 2
    ) -> AnthropicProvider:
        return AnthropicProvider.create(
            "test-key",
            model=model,
            effort=effort,
            max_retries=max_retries,
            http_client=self.http_client(),
        )

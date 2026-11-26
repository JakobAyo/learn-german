"""AnkiConnectClient against httpx2.MockTransport: envelope, error field, unreachable Anki."""

import json
from collections.abc import Callable

import httpx2
import pytest

from learn_german.adapters.anki import API_VERSION, AnkiActionError, AnkiConnectClient
from learn_german.domain.errors import AnkiUnavailableError, FatalError
from tests.integration.anki.mock_ankiconnect import URL

Handler = Callable[[httpx2.Request], httpx2.Response]


def client_for(handler: Handler) -> AnkiConnectClient:
    return AnkiConnectClient(
        URL, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))
    )


def answer(result: object = None, error: str | None = None) -> Handler:
    return lambda _: httpx2.Response(200, json={"result": result, "error": error})


def fail_with(exc: type[httpx2.TransportError]) -> Handler:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise exc("scripted", request=request)

    return handler


def test_client_posts_the_action_envelope_as_json() -> None:
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json={"result": [1, 2], "error": None})

    result = client_for(handler).invoke("findNotes", query='"note:x"')

    (request,) = seen
    assert result == [1, 2]
    assert (request.method, str(request.url)) == ("POST", URL)
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == {
        "action": "findNotes",
        "version": API_VERSION,
        "params": {"query": '"note:x"'},
    }


def test_client_sends_empty_params_for_an_action_without_any() -> None:
    bodies: list[object] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        return httpx2.Response(200, json={"result": ["Default"], "error": None})

    client_for(handler).invoke("deckNames")

    assert bodies == [{"action": "deckNames", "version": 6, "params": {}}]


def test_client_raises_the_error_field_as_a_fatal_action_error() -> None:
    client = client_for(answer(error="model was not found: x"))

    with pytest.raises(AnkiActionError) as caught:
        client.invoke("modelFieldNames", modelName="x")

    assert isinstance(caught.value, FatalError)
    assert (caught.value.action, caught.value.detail) == (
        "modelFieldNames",
        "model was not found: x",
    )


def test_client_returns_a_null_result_without_error() -> None:
    assert client_for(answer(None)).invoke("createDeck", deck="d") is None


def test_client_maps_connection_refused_to_anki_unavailable() -> None:
    client = client_for(fail_with(httpx2.ConnectError))

    with pytest.raises(AnkiUnavailableError, match=r"Cannot reach AnkiConnect at .*Start Anki"):
        client.invoke("version")


def test_client_maps_a_timeout_to_anki_unavailable() -> None:
    client = client_for(fail_with(httpx2.ReadTimeout))

    with pytest.raises(AnkiUnavailableError, match="did not answer 'addNote' in time"):
        client.invoke("addNote")


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(404, text="not found"),
        httpx2.Response(200, text="<html>a web page</html>"),
        httpx2.Response(200, json=6),
        httpx2.Response(200, json={"result": 6}),
    ],
    ids=["http-status", "not-json", "bare-result", "no-error-field"],
)
def test_client_rejects_an_answer_that_is_not_ankiconnects(response: httpx2.Response) -> None:
    client = client_for(lambda _: response)

    with pytest.raises(AnkiUnavailableError, match="AnkiConnect"):
        client.invoke("version")


def test_client_accepts_the_current_ankiconnect_version() -> None:
    assert client_for(answer(6)).require_version() == 6


def test_client_rejects_an_older_ankiconnect() -> None:
    with pytest.raises(AnkiUnavailableError, match="API version 5; learn-german needs 6"):
        client_for(answer(5)).require_version()


@pytest.mark.parametrize("version", ["6", True, None], ids=["string", "bool", "null"])
def test_client_rejects_a_version_that_is_not_a_number(version: object) -> None:
    with pytest.raises(AnkiActionError, match="expected a number"):
        client_for(answer(version)).require_version()


def test_client_builds_its_own_http_client_by_default() -> None:
    assert AnkiConnectClient(URL).url == URL

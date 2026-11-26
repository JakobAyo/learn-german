"""`AnkiConnectClient`: the AnkiConnect JSON envelope over HTTP (0003, 0040)."""

import logging
from typing import Final

import httpx2

from learn_german.adapters.anki.errors import AnkiActionError
from learn_german.domain.errors import AnkiUnavailableError

logger = logging.getLogger(__name__)

API_VERSION: Final = 6
"""AnkiConnect API version sent with every request; it fixes the `result`/`error` envelope."""

DEFAULT_TIMEOUT_SECONDS: Final = 30.0
# Anki runs AnkiConnect actions on its main thread, so an open dialog stalls every request.
# The timeout turns that into a clear error instead of a hang.

_START_ANKI: Final = (
    "Start Anki with the AnkiConnect add-on (code 2055492159) enabled, or set "
    "anki_connect_url to where AnkiConnect listens."
)


class AnkiConnectClient:
    """Sends AnkiConnect actions to the running Anki desktop app.

    Every request is `{"action", "version", "params"}` posted as JSON; every answer is
    `{"result", "error"}`. Raises `AnkiUnavailableError` when nothing answers at the URL,
    the answer is not AnkiConnect's, or AnkiConnect is older than `API_VERSION`, and
    `AnkiActionError` when AnkiConnect reports an error for the action.
    """

    def __init__(
        self,
        url: str,
        *,
        http_client: httpx2.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._url = url
        self._http = http_client if http_client is not None else httpx2.Client(timeout=timeout)

    @property
    def url(self) -> str:
        return self._url

    def invoke(self, action: str, **params: object) -> object:
        """The action's result. Raises `AnkiUnavailableError` or `AnkiActionError`."""
        body = {"action": action, "version": API_VERSION, "params": params}
        try:
            response = self._http.post(self._url, json=body)
        except httpx2.TimeoutException as exc:
            raise AnkiUnavailableError(
                f"AnkiConnect at {self._url} did not answer {action!r} in time. Close any "
                "open dialog in Anki and run the command again."
            ) from exc
        except httpx2.TransportError as exc:
            raise AnkiUnavailableError(
                f"Cannot reach AnkiConnect at {self._url} ({exc}). {_START_ANKI}"
            ) from exc
        result, error = self._unwrap(response, action)
        if error is not None:
            raise AnkiActionError(action, str(error))
        logger.debug("AnkiConnect answered %s", action)
        return result

    def require_version(self) -> int:
        """AnkiConnect's version. Raises `AnkiUnavailableError` if it is older than ours."""
        version = self.invoke("version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise AnkiActionError("version", f"expected a number, got {version!r}")
        if version < API_VERSION:
            raise AnkiUnavailableError(
                f"AnkiConnect at {self._url} speaks API version {version}; learn-german needs "
                f"{API_VERSION} or later. Update the add-on in Anki (Tools, Add-ons)."
            )
        return version

    def _unwrap(self, response: httpx2.Response, action: str) -> tuple[object, object]:
        if response.status_code != httpx2.codes.OK:
            raise AnkiUnavailableError(
                f"{self._url} answered {action!r} with HTTP {response.status_code}, so it is "
                f"not AnkiConnect. {_START_ANKI}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise AnkiUnavailableError(
                f"{self._url} answered {action!r} with something other than JSON, so it is "
                f"not AnkiConnect. {_START_ANKI}"
            ) from exc
        if not isinstance(data, dict) or not {"result", "error"} <= data.keys():
            raise AnkiUnavailableError(
                f"{self._url} answered {action!r} without AnkiConnect's result and error "
                "fields. Update the AnkiConnect add-on, or check anki_connect_url."
            )
        return data["result"], data["error"]

"""The global --verbose option (0048): debug lines on stderr, never the API key.

`sync` runs the real Claude adapter over a scripted Messages API and the real Anki gateway
over a mocked AnkiConnect, so the log lines of both I/O boundaries are produced. The German
text is hand-written (R28).
"""

import re

import pytest
from typer.testing import CliRunner

from learn_german.bootstrap import Overrides
from learn_german.cli.app import EXIT_FATAL, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.extractors import FakeExtractor
from tests.fakes.sources import FakeSource
from tests.integration.anki.mock_ankiconnect import MockAnkiConnect
from tests.integration.llm.mock_api import ScriptedApi, error, message
from tests.integration.llm.test_generation_flow import ANSWER

API_KEY = "sk-ant-api03-Secret_Test-Key-0123456789"
TEXTS = {
    "fake:rathaus": (
        "Nach einer langen Sitzung am Montagabend hat der Stadtrat endlich eine Entscheidung "
        "über den Bau der neuen Brücke getroffen."
    )
}
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

runner = CliRunner()


@pytest.fixture(autouse=True)
def settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", API_KEY)


def _overrides(api: ScriptedApi | None = None) -> Overrides:
    return Overrides(
        clock=FixedClock(),
        extractors=[FakeExtractor()],
        sources=[FakeSource(TEXTS)],
        llm_http_client=(api or ScriptedApi([message(ANSWER)])).http_client(),
        anki_http_client=MockAnkiConnect().http_client(),
    )


def _run(*args: str, overrides: Overrides) -> tuple[int, str, str]:
    result = runner.invoke(create_app(overrides), list(args))
    return (
        result.exit_code,
        _ANSI_ESCAPE.sub("", result.stdout),
        _ANSI_ESCAPE.sub("", result.stderr),
    )


def _add(overrides: Overrides) -> None:
    assert _run("add", *TEXTS, overrides=overrides)[0] == 0


def test_without_verbose_no_debug_lines_are_written() -> None:
    overrides = _overrides()
    _add(overrides)

    code, out, err = _run("sync", "--dry-run", overrides=overrides)

    assert code == 0
    assert "would add" in out
    assert "DEBUG" not in out + err
    assert "INFO" not in out + err


def test_verbose_logs_the_io_boundaries_on_stderr() -> None:
    overrides = _overrides()
    _add(overrides)

    code, out, err = _run("--verbose", "sync", overrides=overrides)

    assert code == 0
    assert "DEBUG" not in out
    for line in (
        "Reading settings from",
        "Opened the database at",
        "DEBUG learn_german.adapters.anki.client: AnkiConnect answered version",
        "Selected 1 of 1 pending chunks",
        "LLM cache miss for entscheidung|treffen; asking anthropic",
        "Calling Claude claude-opus-5-5 for entscheidung|treffen at medium effort",
        "Claude answered for entscheidung|treffen: request req_01",
        "AnkiConnect answered addNote",
    ):
        assert line in err


def test_short_option_and_add_log_the_extraction() -> None:
    code, _, err = _run("-v", "add", *TEXTS, overrides=_overrides())

    assert code == 0
    assert "The nvv extractor found 1 occurrences of 1 chunks" in err


def test_verbose_never_writes_the_api_key() -> None:
    overrides = _overrides()
    _add(overrides)

    code, out, err = _run("-v", "sync", "--dry-run", overrides=overrides)

    assert code == 0
    assert API_KEY not in out + err
    assert API_KEY[:20] not in out + err


def test_verbose_never_writes_the_api_key_when_it_is_rejected() -> None:
    overrides = _overrides(ScriptedApi([error(401, "authentication_error")]))
    _add(overrides)

    code, out, err = _run("-v", "sync", overrides=overrides)

    assert code == EXIT_FATAL
    assert "The Claude API rejected the API key" in err
    assert API_KEY[:20] not in out + err

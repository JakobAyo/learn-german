"""`add`, `status` and `reextract` through typer's CliRunner, with real SQLite and fakes."""

import re
import shutil
from pathlib import Path

import httpx2
import pytest
from typer.testing import CliRunner

from learn_german.bootstrap import Overrides
from learn_german.cli.app import EXIT_FATAL, EXIT_ITEM_FAILED, create_app
from learn_german.domain.errors import NlpModelMissingError
from learn_german.domain.models import Candidate, ChunkKey
from tests.fakes.clock import FixedClock
from tests.fakes.extractors import FakeExtractor

DATA = Path(__file__).parent.parent / "data" / "sources"
URL = "https://zeitung.example/politik/radwege"
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

runner = CliRunner()


def plain(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def site(request: httpx2.Request) -> httpx2.Response:
    if str(request.url) == URL:
        html = (DATA / "article.html").read_bytes()
        return httpx2.Response(200, headers={"content-type": "text/html"}, content=html)
    return httpx2.Response(404)


def overrides(extractor: FakeExtractor | None = None) -> Overrides:
    return Overrides(
        clock=FixedClock(),
        extractors=[extractor or FakeExtractor()],
        http_client=httpx2.Client(transport=httpx2.MockTransport(site)),
    )


def invoke(*args: str, extractor: FakeExtractor | None = None) -> tuple[int, str, str]:
    result = runner.invoke(create_app(overrides(extractor)), list(args))
    return result.exit_code, plain(result.stdout), plain(result.stderr)


@pytest.fixture
def article() -> Path:
    """The fixture article copied into the working directory, which is tmp_path/work."""
    return Path(shutil.copy(DATA / "artikel.txt", "artikel.txt"))


@pytest.mark.usefixtures("article")
def test_add_file_prints_counts_and_exits_zero() -> None:
    code, out, _ = invoke("add", "artikel.txt")

    assert code == 0
    assert 'added      artikel.txt "artikel": 4 chunks (4 new), 4 occurrences' in out
    assert "1 source: 1 added." in out


@pytest.mark.usefixtures("article")
def test_add_url_uses_the_news_source() -> None:
    code, out, _ = invoke("add", URL)

    assert code == 0
    assert f'{URL} "Neue Radwege für Beispielstadt": 4 chunks (4 new)' in out


def test_add_twice_skips_and_exits_zero(article: Path) -> None:
    invoke("add", "artikel.txt")

    code, out, _ = invoke("add", str(article))

    assert code == 0
    assert "skipped" in out
    assert "--force" in out


@pytest.mark.usefixtures("article")
def test_add_from_list_processes_every_line_and_exits_one_on_failure() -> None:
    Path("quellen.txt").write_text(
        f"# Meine Quellen\n\nartikel.txt\n{URL}\nhttps://zeitung.example/fehlt\n",
        encoding="utf-8",
    )

    code, out, _ = invoke("add", "--from", "quellen.txt")

    assert code == EXIT_ITEM_FAILED
    assert out.count("added ") == 2
    assert "failed     https://zeitung.example/fehlt: " in out
    assert "3 sources: 2 added, 1 failed." in out


@pytest.mark.usefixtures("article")
def test_add_force_refreshes_a_known_source() -> None:
    invoke("add", "artikel.txt")

    code, out, _ = invoke("add", "--force", "artikel.txt")

    assert code == 0
    assert "refreshed" in out
    assert "4 chunks (0 new)" in out


def test_add_without_references_is_a_usage_error() -> None:
    code, _, err = invoke("add")

    assert code == EXIT_FATAL
    assert "at least one URL or file" in err


def test_add_from_a_missing_list_is_a_usage_error() -> None:
    code, _, err = invoke("add", "--from", "fehlt.txt")

    assert code == EXIT_FATAL
    assert "cannot read fehlt.txt" in err


class MissingModel(FakeExtractor):
    def extract(self, text: str) -> list[Candidate]:
        raise NlpModelMissingError("The spaCy model de_core_news_lg is not installed.")


@pytest.mark.usefixtures("article")
def test_add_stops_with_exit_two_on_a_fatal_error() -> None:
    code, out, err = invoke("add", "artikel.txt", URL, extractor=MissingModel())

    assert code == EXIT_FATAL
    assert "Error: The spaCy model de_core_news_lg is not installed." in err
    assert "added" not in out


def test_invalid_settings_are_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEARN_GERMAN_CAP", "viele")

    code, _, err = invoke("status")

    assert code == EXIT_FATAL
    assert "Error: Invalid settings" in err


def test_status_on_an_empty_database_says_how_to_start() -> None:
    code, out, _ = invoke("status")

    assert code == 0
    assert "No sources yet" in out


@pytest.mark.usefixtures("article")
def test_status_lists_sources_and_ranked_pending_chunks() -> None:
    invoke("add", "artikel.txt", URL)

    code, out, _ = invoke("status", "--top", "2")

    assert code == 0
    assert "2 sources stored." in out
    assert '"Neue Radwege für Beispielstadt" (4 occurrences)  ' + URL in out
    assert "4 chunks pending." in out
    assert re.search(r"1\. entscheidung\|treffen\s+2 occurrences", out)
    assert "3." not in out


def test_reextract_applies_a_changed_extractor(article: Path) -> None:
    invoke("add", "artikel.txt")
    narrower = FakeExtractor({"Entscheidung": ChunkKey("entscheidung|treffen")})

    code, out, _ = invoke("reextract", extractor=narrower)

    assert code == 0
    assert f"{article.resolve()}: 1 kept, 0 new, 3 removed" in out
    assert "Extracted 1 source again: 0 new occurrences, 3 removed." in out


def test_reextract_without_sources_says_so() -> None:
    code, out, _ = invoke("reextract")

    assert code == 0
    assert "nothing to extract again" in out

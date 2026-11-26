"""SourceAdapter contract, run against FakeSource and both real adapters."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx2
import pytest

from learn_german.adapters.sources import LocalFileSource, NewsUrlSource
from learn_german.domain.errors import ItemError
from learn_german.ports import SourceAdapter
from tests.fakes.clock import DEFAULT_NOW, FixedClock
from tests.fakes.sources import FakeSource

ARTICLE = (Path(__file__).parent.parent / "data" / "sources" / "article.html").read_bytes()


@dataclass(frozen=True, slots=True)
class Subject:
    adapter: SourceAdapter
    readable: str
    unreadable: str


def fake(_: Path) -> Subject:
    return Subject(FakeSource({"fake:a": "Ein Text."}), "fake:a", "fake:fehlt")


def local_file(tmp_path: Path) -> Subject:
    (tmp_path / "a.txt").write_text("Ein Text.", encoding="utf-8")
    return Subject(LocalFileSource(FixedClock()), str(tmp_path / "a.txt"), "fehlt.txt")


def news_url(_: Path) -> Subject:
    def site(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/a":
            return httpx2.Response(200, headers={"content-type": "text/html"}, content=ARTICLE)
        return httpx2.Response(404)

    client = httpx2.Client(transport=httpx2.MockTransport(site))
    adapter = NewsUrlSource(client, FixedClock(), user_agent="learn-german/test")
    return Subject(adapter, "https://zeitung.example/a", "https://zeitung.example/fehlt")


@pytest.fixture(params=[fake, local_file, news_url], ids=["fake", "local-file", "news-url"])
def subject(request: pytest.FixtureRequest, tmp_path: Path) -> Subject:
    factory: Callable[[Path], Subject] = request.param
    return factory(tmp_path)


def test_source_adapter_handles_its_own_references_only(subject: Subject) -> None:
    assert subject.adapter.can_handle(subject.readable)
    assert subject.adapter.can_handle(subject.unreadable)
    assert not subject.adapter.can_handle("mailto:redaktion@zeitung.example")


def test_source_adapter_fetch_returns_text_under_the_reference(subject: Subject) -> None:
    source = subject.adapter.fetch(subject.readable)

    assert source.ref == subject.readable
    assert source.text
    assert source.content_hash
    assert source.fetched_at == DEFAULT_NOW


def test_source_adapter_same_text_gives_same_hash(subject: Subject) -> None:
    first = subject.adapter.fetch(subject.readable)
    second = subject.adapter.fetch(subject.readable)

    assert first.content_hash == second.content_hash


def test_source_adapter_unreadable_reference_is_an_item_error(subject: Subject) -> None:
    with pytest.raises(ItemError):
        subject.adapter.fetch(subject.unreadable)

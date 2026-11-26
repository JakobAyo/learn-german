"""NewsUrlSource against httpx2.MockTransport: robots.txt, refusals, paywalls, timeouts."""

from collections.abc import Callable, Mapping
from pathlib import Path

import httpx2
import pytest

from learn_german.adapters.sources import NewsUrlSource, content_hash
from learn_german.adapters.sources.news_url import MAX_REDIRECTS
from learn_german.domain.errors import ItemError, SourceFetchError
from learn_german.domain.models import SourceKind
from tests.fakes.clock import DEFAULT_NOW, FixedClock

DATA = Path(__file__).parent.parent.parent / "data" / "sources"
ARTICLE_HTML = (DATA / "article.html").read_bytes()
TEASER_HTML = (DATA / "teaser.html").read_bytes()
URL = "https://zeitung.example/politik/radwege"
ROBOTS = "https://zeitung.example/robots.txt"
USER_AGENT = "learn-german/0.0-test"
HTML = {"content-type": "text/html; charset=utf-8"}

Route = httpx2.Response | Callable[[httpx2.Request], httpx2.Response]


class Site:
    """A scripted web site that records every URL requested from it."""

    def __init__(self, routes: Mapping[str, Route]) -> None:
        self.routes = dict(routes)
        self.requested: list[str] = []
        self.user_agents: list[str] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        self.requested.append(url)
        self.user_agents.append(request.headers["user-agent"])
        route = self.routes.get(url, httpx2.Response(404))
        return route(request) if callable(route) else route


def source_for(site: Site) -> NewsUrlSource:
    client = httpx2.Client(transport=httpx2.MockTransport(site))
    return NewsUrlSource(client, FixedClock(), user_agent=USER_AGENT)


def article(html: bytes = ARTICLE_HTML) -> httpx2.Response:
    return httpx2.Response(200, headers=HTML, content=html)


def robots(text: str) -> httpx2.Response:
    return httpx2.Response(200, text=text)


def test_news_source_handles_only_http_urls() -> None:
    source = source_for(Site({}))

    assert source.can_handle(URL)
    assert source.can_handle("http://zeitung.example/a")
    assert not source.can_handle("artikel.txt")
    assert not source.can_handle("ftp://zeitung.example/a")
    assert not source.can_handle("https://")


def test_news_source_returns_main_text_title_and_hash() -> None:
    site = Site({ROBOTS: robots("User-agent: *\nDisallow: /intern/\n"), URL: article()})

    source = source_for(site).fetch(URL)

    assert (source.ref, source.kind, source.fetched_at) == (URL, SourceKind.NEWS_URL, DEFAULT_NOW)
    assert source.title == "Neue Radwege für Beispielstadt"
    assert source.text.startswith("Der Stadtrat von Beispielstadt hat am Dienstag")
    assert "Impressum" not in source.text
    assert "Neue Radwege für Beispielstadt" not in source.text
    assert "\n\nDie Bürgermeisterin nahm" in source.text
    assert source.content_hash == content_hash(source.text)
    assert site.requested == [ROBOTS, URL]
    assert set(site.user_agents) == {USER_AGENT}


def test_news_source_never_requests_a_page_robots_txt_disallows() -> None:
    site = Site({ROBOTS: robots("User-agent: learn-german\nDisallow: /politik/\n"), URL: article()})

    with pytest.raises(SourceFetchError, match=r"robots\.txt does not allow.*\.txt file"):
        source_for(site).fetch(URL)

    assert URL not in site.requested
    assert site.requested == [ROBOTS]


@pytest.mark.parametrize(
    ("robots_response", "allowed"),
    [
        pytest.param(httpx2.Response(404), True, id="missing-allows"),
        pytest.param(httpx2.Response(403), False, id="forbidden-disallows"),
        pytest.param(robots("User-agent: *\nDisallow: /\n"), False, id="disallow-all"),
        pytest.param(robots("User-agent: otherbot\nDisallow: /\n"), True, id="other-agent"),
    ],
)
def test_news_source_reads_robots_status_like_the_standard_library(
    robots_response: httpx2.Response, allowed: bool
) -> None:
    site = Site({ROBOTS: robots_response, URL: article()})

    if allowed:
        source_for(site).fetch(URL)
    else:
        with pytest.raises(SourceFetchError, match="robots"):
            source_for(site).fetch(URL)

    assert (URL in site.requested) is allowed


def test_news_source_fails_when_robots_txt_has_a_server_error() -> None:
    site = Site({ROBOTS: httpx2.Response(503), URL: article()})

    with pytest.raises(SourceFetchError, match=r"HTTP 503 for its robots\.txt"):
        source_for(site).fetch(URL)

    assert URL not in site.requested


@pytest.mark.parametrize("status", [401, 402, 403])
def test_news_source_reports_refused_pages_with_the_txt_fallback(status: int) -> None:
    site = Site({ROBOTS: httpx2.Response(404), URL: httpx2.Response(status)})

    with pytest.raises(SourceFetchError, match=rf"HTTP {status}.*paywall.*\.txt file"):
        source_for(site).fetch(URL)


@pytest.mark.parametrize(
    ("status", "message"),
    [
        pytest.param(404, "does not exist", id="not-found"),
        pytest.param(429, "slow down", id="rate-limited"),
        pytest.param(500, "HTTP 500", id="server-error"),
    ],
)
def test_news_source_reports_other_http_errors(status: int, message: str) -> None:
    site = Site({ROBOTS: httpx2.Response(404), URL: httpx2.Response(status)})

    with pytest.raises(SourceFetchError, match=message):
        source_for(site).fetch(URL)


def test_news_source_rejects_paywall_teasers_as_too_short() -> None:
    site = Site({ROBOTS: httpx2.Response(404), URL: article(TEASER_HTML)})

    with pytest.raises(SourceFetchError, match=r"Only \d+ words.*paywall.*\.txt file"):
        source_for(site).fetch(URL)


def test_news_source_rejects_pages_without_main_text() -> None:
    site = Site({ROBOTS: httpx2.Response(404), URL: article(b"<html><body></body></html>")})

    with pytest.raises(SourceFetchError, match="Only 0 words"):
        source_for(site).fetch(URL)


def test_news_source_rejects_content_that_is_not_a_web_page() -> None:
    pdf = httpx2.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
    site = Site({ROBOTS: httpx2.Response(404), URL: pdf})

    with pytest.raises(SourceFetchError, match="not a web page"):
        source_for(site).fetch(URL)


def _raise(exc_type: type[httpx2.TransportError]) -> Callable[[httpx2.Request], httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise exc_type("scripted", request=request)

    return handler


@pytest.mark.parametrize(
    ("exc_type", "message"),
    [
        pytest.param(httpx2.ReadTimeout, "did not answer within 20 seconds", id="timeout"),
        pytest.param(httpx2.ConnectError, "Cannot fetch", id="unreachable"),
    ],
)
def test_news_source_turns_transport_failures_into_item_errors(
    exc_type: type[httpx2.TransportError], message: str
) -> None:
    site = Site({ROBOTS: httpx2.Response(404), URL: _raise(exc_type)})

    with pytest.raises(ItemError, match=message):
        source_for(site).fetch(URL)


def test_news_source_times_out_on_robots_txt_without_fetching_the_page() -> None:
    site = Site({ROBOTS: _raise(httpx2.ConnectTimeout), URL: article()})

    with pytest.raises(SourceFetchError, match="did not answer"):
        source_for(site).fetch(URL)

    assert site.requested == [ROBOTS]


def test_news_source_checks_robots_again_when_a_redirect_changes_site() -> None:
    moved = "https://www.zeitung.example/politik/radwege"
    site = Site(
        {
            ROBOTS: httpx2.Response(404),
            URL: httpx2.Response(301, headers={"location": moved}),
            "https://www.zeitung.example/robots.txt": robots("User-agent: *\nDisallow: /\n"),
            moved: article(),
        }
    )

    with pytest.raises(SourceFetchError, match="robots"):
        source_for(site).fetch(URL)

    assert moved not in site.requested


def test_news_source_follows_a_relative_redirect_on_the_same_site() -> None:
    moved = "https://zeitung.example/politik/radwege-neu"
    site = Site(
        {
            ROBOTS: httpx2.Response(404),
            URL: httpx2.Response(302, headers={"location": "/politik/radwege-neu"}),
            moved: article(),
        }
    )

    source = source_for(site).fetch(URL)

    assert source.ref == URL
    assert site.requested == [ROBOTS, URL, moved]


def test_news_source_stops_after_too_many_redirects() -> None:
    def loop(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(302, headers={"location": str(request.url) + "x"})

    routes: dict[str, Route] = {ROBOTS: httpx2.Response(404)}
    routes.update({URL + "x" * hop: loop for hop in range(MAX_REDIRECTS + 1)})

    with pytest.raises(SourceFetchError, match="redirected more than"):
        source_for(Site(routes)).fetch(URL)


def test_news_source_reads_robots_txt_once_per_site() -> None:
    other = "https://zeitung.example/wirtschaft/haushalt"
    site = Site({ROBOTS: httpx2.Response(404), URL: article(), other: article()})
    source = source_for(site)

    source.fetch(URL)
    source.fetch(other)

    assert site.requested == [ROBOTS, URL, other]

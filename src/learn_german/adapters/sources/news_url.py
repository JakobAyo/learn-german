"""`NewsUrlSource`: fetch one article page politely and keep its main text (R4, 0013, 0043)."""

import logging
import warnings
from dataclasses import dataclass
from typing import Final
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx2

from learn_german.adapters.sources.text import (
    PARAGRAPH_SEPARATOR,
    content_hash,
    normalise_text,
    word_count,
)
from learn_german.domain.errors import SourceFetchError
from learn_german.domain.models import Source, SourceKind
from learn_german.ports import Clock

logger = logging.getLogger(__name__)

ROBOTS_AGENT: Final = "learn-german"
"""The name robots.txt rules are matched against."""

MIN_WORDS: Final = 150
"""Fewer words of main text than this usually means a paywall teaser or a login page."""

MAX_REDIRECTS: Final = 5
TIMEOUT_SECONDS: Final = 20.0
_SCHEMES = frozenset({"http", "https"})
_BLOCKED = frozenset({401, 402, 403})
_FALLBACK: Final = (
    "If you can read the article in a browser, save its text as a UTF-8 .txt file and run "
    "`learn-german add` on that file."
)


@dataclass(frozen=True, slots=True)
class Article:
    """Main text and title that trafilatura found in a page."""

    text: str
    title: str | None


class NewsUrlSource:
    """Implements `ports.SourceAdapter` for article URLs (R4).

    Fetches only the URL it is given, never links from the page (0013). Before each request
    to a site it reads that site's robots.txt, and it follows at most `MAX_REDIRECTS`
    redirects, checking robots.txt again whenever a redirect leads to another site. The
    main text comes from trafilatura. Raises `SourceFetchError` when robots.txt forbids the
    page, the site refuses it (401, 402, 403), the request fails or times out, or the page
    yields fewer than `min_words` words; each message points to the `.txt` fallback.
    """

    def __init__(
        self,
        http_client: httpx2.Client,
        clock: Clock,
        *,
        user_agent: str,
        min_words: int = MIN_WORDS,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        self._http = http_client
        self._clock = clock
        self._headers = {"User-Agent": user_agent}
        self._min_words = min_words
        self._timeout = timeout
        self._robots: dict[str, RobotFileParser] = {}

    def can_handle(self, ref: str) -> bool:
        parts = urlsplit(ref)
        return parts.scheme in _SCHEMES and bool(parts.netloc)

    def fetch(self, ref: str) -> Source:
        response = self._get_article(ref)
        article = _main_text(response.content, str(response.url))
        words = 0 if article is None else word_count(article.text)
        if article is None or words < self._min_words:
            raise SourceFetchError(
                f"Only {words} words of article text came out of {ref}; at least "
                f"{self._min_words} are needed. That usually means a paywall, a login or a "
                f"page that is not an article. {_FALLBACK}"
            )
        return Source(
            ref=ref,
            kind=SourceKind.NEWS_URL,
            title=article.title,
            fetched_at=self._clock.now(),
            content_hash=content_hash(article.text),
            text=article.text,
        )

    def _get_article(self, ref: str) -> httpx2.Response:
        url = ref
        for _ in range(MAX_REDIRECTS + 1):
            self._require_allowed(url, ref)
            response = self._get(url, ref, follow_redirects=False)
            location = response.headers.get("location")
            if not (response.is_redirect and location):
                _require_ok(response, ref)
                return response
            url = urljoin(url, location)
            logger.debug("%s redirects to %s", ref, url)
        raise SourceFetchError(f"{ref} redirected more than {MAX_REDIRECTS} times. {_FALLBACK}")

    def _require_allowed(self, url: str, ref: str) -> None:
        if not self._robots_for(url, ref).can_fetch(ROBOTS_AGENT, url):
            raise SourceFetchError(
                f"The site's robots.txt does not allow automated fetching of {url}, so "
                f"learn-german leaves it alone. {_FALLBACK}"
            )

    def _robots_for(self, url: str, ref: str) -> RobotFileParser:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._read_robots(origin, ref)
        return self._robots[origin]

    def _read_robots(self, origin: str, ref: str) -> RobotFileParser:
        response = self._get(f"{origin}/robots.txt", ref, follow_redirects=True)
        status = response.status_code
        # The same reading of status codes as urllib.robotparser.RobotFileParser.read().
        if status in (401, 403):
            lines = ["User-agent: *", "Disallow: /"]
        elif 400 <= status < 500:
            lines = []
        elif status >= 500:
            raise SourceFetchError(
                f"{origin} answered HTTP {status} for its robots.txt, so learn-german cannot "
                f"tell whether it may fetch {ref}. Try again later. {_FALLBACK}"
            )
        else:
            lines = response.text.splitlines()
        parser = RobotFileParser(f"{origin}/robots.txt")
        parser.parse(lines)
        return parser

    def _get(self, url: str, ref: str, *, follow_redirects: bool) -> httpx2.Response:
        try:
            return self._http.get(
                url,
                headers=self._headers,
                follow_redirects=follow_redirects,
                timeout=self._timeout,
            )
        except httpx2.TimeoutException as exc:
            raise SourceFetchError(
                f"{url} did not answer within {self._timeout:g} seconds while fetching {ref}. "
                f"Try again later. {_FALLBACK}"
            ) from exc
        except (httpx2.HTTPError, httpx2.InvalidURL) as exc:
            raise SourceFetchError(
                f"Cannot fetch {url} for {ref} ({exc}). Check the address and your network "
                f"connection. {_FALLBACK}"
            ) from exc


def _require_ok(response: httpx2.Response, ref: str) -> None:
    status = response.status_code
    if status in _BLOCKED:
        raise SourceFetchError(
            f"{ref} refused access (HTTP {status}), probably a paywall or login. "
            f"learn-german does not get around those. {_FALLBACK}"
        )
    if status in (404, 410):
        raise SourceFetchError(f"{ref} does not exist (HTTP {status}). Check the address.")
    if status == 429:
        raise SourceFetchError(f"{ref} asks to slow down (HTTP 429). Try again later.")
    if not response.is_success:
        raise SourceFetchError(f"{ref} answered HTTP {status}. Try again later. {_FALLBACK}")
    content_type = response.headers.get("content-type", "html").lower()
    if "html" not in content_type and "xml" not in content_type:
        raise SourceFetchError(
            f"{ref} is not a web page (content type {content_type}). Download the text and "
            "add it as a UTF-8 .txt file."
        )


def _main_text(html: bytes, url: str) -> Article | None:
    """The page's main text, one paragraph per block, or None if trafilatura finds none."""
    with warnings.catch_warnings():
        # Importing trafilatura imports urllib3's SOCKS support, which warns if PySocks is
        # missing. trafilatura never fetches here, so the warning is noise for the user.
        warnings.simplefilter("ignore")
        # Imported here, not at the top: it is slow and only `add` on a URL needs it.
        import trafilatura
        from trafilatura.settings import Document
    document = trafilatura.bare_extraction(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        with_metadata=True,
    )
    if not isinstance(document, Document) or not document.text:
        return None
    title = document.title or None
    # trafilatura puts each paragraph on one line; the stored text separates them by a blank
    # line, as the NLP parser expects. The headline repeats the title, so it is dropped.
    lines = [line for line in document.text.splitlines() if line.strip()]
    if lines and title is not None and lines[0].strip() == title.strip():
        lines = lines[1:]
    return Article(normalise_text(PARAGRAPH_SEPARATOR.join(lines)), title)

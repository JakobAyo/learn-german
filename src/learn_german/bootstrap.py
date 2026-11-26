"""Composition root: reads settings and wires adapters into use cases (0018).

Tests replace plug-ins through `Overrides`; everything else is built from `Settings`.
"""

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version

import httpx2

from learn_german.adapters.anki import AnkiConnectClient, AnkiConnectGateway
from learn_german.adapters.anki.client import DEFAULT_TIMEOUT_SECONDS
from learn_german.adapters.clock import SystemClock
from learn_german.adapters.llm import AnthropicProvider
from learn_german.adapters.llm.claude import PROVIDER_NAME as ANTHROPIC
from learn_german.adapters.nlp import NvvExtractor
from learn_german.adapters.sources import LocalFileSource, NewsUrlSource
from learn_german.adapters.storage.sqlite import SqliteUnitOfWork, open_database
from learn_german.application.add_sources import AddSources
from learn_german.application.generation import CachingProvider, CheckedProvider
from learn_german.application.reextract import Reextract
from learn_german.application.selection import (
    AlreadyInDeckFilter,
    ChunkSelector,
    FilterChain,
    OccurrenceRanker,
    ShortestSentencePicker,
)
from learn_german.application.status import ShowStatus
from learn_german.application.sync import SyncService
from learn_german.config import APP_NAME, ENV_PREFIX, Settings
from learn_german.domain.errors import ConfigError
from learn_german.domain.models import ChunkKind
from learn_german.ports import (
    AnkiGateway,
    ChunkExtractor,
    Clock,
    LLMProvider,
    SourceAdapter,
    UnitOfWork,
)


def extractor_registry() -> dict[str, ChunkExtractor]:
    """Chunk extractors by name (R9). Cheap to build: the spaCy model loads on first use."""
    return {ChunkKind.NVV.value: NvvExtractor.default()}


def _anthropic_provider(settings: Settings, http_client: httpx2.Client | None) -> LLMProvider:
    return AnthropicProvider.create(
        settings.require_anthropic_api_key(), model=settings.model, http_client=http_client
    )


LLMFactory = Callable[[Settings, httpx2.Client | None], LLMProvider]

LLM_PROVIDERS: Mapping[str, LLMFactory] = {ANTHROPIC: _anthropic_provider}
"""LLM provider factories by the `provider` setting (R17). Each checks its own credentials
and uses the given HTTP client, or its own when it is None."""


def llm_provider(settings: Settings, http_client: httpx2.Client | None = None) -> LLMProvider:
    """The configured provider, without the check and cache decorators.

    Raises `ConfigError` for an unknown provider and `MissingCredentialsError` if its API
    key is not set. Nothing is sent to the provider here.
    """
    factory = LLM_PROVIDERS.get(settings.provider)
    if factory is None:
        raise ConfigError(
            f"Unknown LLM provider {settings.provider!r}. Set provider in config.toml or "
            f"{ENV_PREFIX}PROVIDER to one of: {', '.join(LLM_PROVIDERS)}."
        )
    return factory(settings, http_client)


def generation_stack(provider: LLMProvider, uow: UnitOfWork, clock: Clock) -> LLMProvider:
    """Checks inside the cache, so only content that passed is cached (0036)."""
    return CachingProvider(CheckedProvider(provider), uow, clock)


def user_agent() -> str:
    """The honest User-Agent of every web request, naming the tool and its version (0013)."""
    return f"{APP_NAME}/{version(APP_NAME)}"


def source_adapters(http_client: httpx2.Client, clock: Clock) -> list[SourceAdapter]:
    """Source adapters in the order they are asked; the first that handles a ref wins."""
    return [
        NewsUrlSource(http_client, clock, user_agent=user_agent()),
        LocalFileSource(clock),
    ]


@dataclass(frozen=True, slots=True)
class Overrides:
    """Plug-ins to use instead of the real ones, for tests. `None` builds the real one."""

    clock: Clock | None = None
    extractors: Sequence[ChunkExtractor] | None = None
    sources: Sequence[SourceAdapter] | None = None
    http_client: httpx2.Client | None = None
    """Used by the real source adapters, for example with an `httpx2.MockTransport`."""
    provider: LLMProvider | None = None
    """Replaces the configured LLM provider; `sync` still wraps it in the checks and cache."""
    anki: AnkiGateway | None = None
    anki_http_client: httpx2.Client | None = None
    """Used by the real Anki gateway when `anki` is not given, for example with a mock."""
    llm_http_client: httpx2.Client | None = None
    """Used by the real LLM provider when `provider` is not given, for example with a mock."""


@dataclass(frozen=True, slots=True)
class IngestServices:
    """The use cases behind `add`, `status` and `reextract`, sharing one database."""

    add_sources: AddSources
    show_status: ShowStatus
    reextract: Reextract


@contextmanager
def ingest_services(
    settings: Settings, overrides: Overrides | None = None
) -> Iterator[IngestServices]:
    """Open the database and wire the ingest use cases; close everything on exit.

    Raises `DatabaseError` if the database cannot be opened or migrated.
    """
    overrides = overrides or Overrides()
    clock = overrides.clock or SystemClock()
    uow = SqliteUnitOfWork(open_database(settings.database_path))
    http_client = overrides.http_client or httpx2.Client()
    try:
        sources = (
            overrides.sources
            if overrides.sources is not None
            else source_adapters(http_client, clock)
        )
        extractors = (
            overrides.extractors
            if overrides.extractors is not None
            else list(extractor_registry().values())
        )
        yield IngestServices(
            add_sources=AddSources(uow, sources, extractors),
            show_status=ShowStatus(uow, OccurrenceRanker()),
            reextract=Reextract(uow, extractors),
        )
    finally:
        uow.close()
        if overrides.http_client is None:
            http_client.close()


@contextmanager
def sync_service(settings: Settings, overrides: Overrides | None = None) -> Iterator[SyncService]:
    """Check the settings `sync` needs, open the database and wire `SyncService` (0046).

    The hint language and the provider's API key are checked first, before the database is
    opened or Anki asked. Raises `ConfigError` without a hint language or with an unknown
    provider, `MissingCredentialsError` without an API key, and `DatabaseError` if the
    database cannot be opened.
    """
    overrides = overrides or Overrides()
    hint_language = settings.require_hint_language()  # R16, 0015
    provider = overrides.provider or llm_provider(settings, overrides.llm_http_client)
    clock = overrides.clock or SystemClock()
    uow = SqliteUnitOfWork(open_database(settings.database_path))
    anki_http = overrides.anki_http_client or httpx2.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        gateway = overrides.anki or AnkiConnectGateway(
            AnkiConnectClient(settings.anki_connect_url, http_client=anki_http),
            deck=settings.deck,
        )
        ranker, picker = OccurrenceRanker(), ShortestSentencePicker()
        yield SyncService(
            uow=uow,
            gateway=gateway,
            provider=generation_stack(provider, uow, clock),
            selector=ChunkSelector(
                uow, FilterChain([AlreadyInDeckFilter(gateway)]), ranker, picker
            ),
            offline_selector=ChunkSelector(uow, FilterChain(), ranker, picker),
            clock=clock,
            hint_language=hint_language,
        )
    finally:
        uow.close()
        if overrides.anki_http_client is None:
            anki_http.close()

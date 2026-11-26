"""Composition root: reads settings and wires adapters into use cases (0018).

Tests replace plug-ins through `Overrides`; everything else is built from `Settings`.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version

import httpx2

from learn_german.adapters.clock import SystemClock
from learn_german.adapters.nlp import NvvExtractor
from learn_german.adapters.sources import LocalFileSource, NewsUrlSource
from learn_german.adapters.storage.sqlite import SqliteUnitOfWork, open_database
from learn_german.application.add_sources import AddSources
from learn_german.application.reextract import Reextract
from learn_german.application.selection import OccurrenceRanker
from learn_german.application.status import ShowStatus
from learn_german.config import APP_NAME, Settings
from learn_german.domain.models import ChunkKind
from learn_german.ports import ChunkExtractor, Clock, SourceAdapter


def extractor_registry() -> dict[str, ChunkExtractor]:
    """Chunk extractors by name (R9). Cheap to build: the spaCy model loads on first use."""
    return {ChunkKind.NVV.value: NvvExtractor.default()}


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

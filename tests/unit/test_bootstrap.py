import httpx2
import pytest

from learn_german.adapters.llm import AnthropicProvider
from learn_german.adapters.sources import LocalFileSource, NewsUrlSource
from learn_german.application.generation import CachingProvider
from learn_german.bootstrap import (
    Overrides,
    ingest_services,
    llm_provider,
    source_adapters,
    sync_service,
    user_agent,
)
from learn_german.config import load_settings
from learn_german.domain.errors import ConfigError, MissingCredentialsError
from tests.fakes.anki import FakeAnkiGateway
from tests.fakes.clock import FixedClock


def test_user_agent_names_the_tool_and_its_version() -> None:
    assert user_agent().startswith("learn-german/")


def test_source_adapters_ask_the_news_source_before_the_file_source() -> None:
    with httpx2.Client() as client:
        adapters = source_adapters(client, FixedClock())

    assert [type(adapter) for adapter in adapters] == [NewsUrlSource, LocalFileSource]


def test_ingest_services_wire_real_adapters_and_open_the_database() -> None:
    settings = load_settings()

    with ingest_services(settings) as services:
        report = services.show_status.run()

    assert report.source_count == 0
    assert settings.database_path.exists()


def test_llm_provider_builds_the_claude_provider_with_the_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("LEARN_GERMAN_MODEL", "claude-haiku-5-5")

    provider = llm_provider(load_settings())

    assert isinstance(provider, AnthropicProvider)
    assert (provider.name, provider.model) == ("anthropic", "claude-haiku-5-5")


def test_llm_provider_needs_a_known_provider_and_its_key(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(MissingCredentialsError):
        llm_provider(load_settings())
    monkeypatch.setenv("LEARN_GERMAN_PROVIDER", "deepseek")
    with pytest.raises(ConfigError, match="one of: anthropic"):
        llm_provider(load_settings())


def test_sync_service_wraps_the_real_provider_in_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    anki = FakeAnkiGateway()

    with sync_service(load_settings(), Overrides(anki=anki)) as service:
        run = service.start(cap=10, dry_run=False)

    assert isinstance(service.provider, CachingProvider)
    assert run.selected == ()
    assert anki.setup_calls == 1


def test_sync_service_checks_the_api_key_before_opening_the_database() -> None:
    settings = load_settings()

    with pytest.raises(MissingCredentialsError, match="ANTHROPIC_API_KEY"), sync_service(settings):
        pass

    assert not settings.database_path.exists()

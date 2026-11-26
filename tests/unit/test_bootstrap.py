import httpx2

from learn_german.adapters.sources import LocalFileSource, NewsUrlSource
from learn_german.bootstrap import ingest_services, source_adapters, user_agent
from learn_german.config import load_settings
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

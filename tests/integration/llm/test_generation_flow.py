"""M5 done-when: a chunk becomes checked CardContent through the real adapter with mocked
HTTP, and a second identical call makes no HTTP request (0004, 0036)."""

import json
from collections.abc import Iterator

import pytest

from learn_german.adapters.storage.sqlite import MEMORY, SqliteUnitOfWork, open_database
from learn_german.application.generation import CachingProvider, CheckedProvider
from learn_german.domain.errors import GenerationError
from learn_german.ports import LLMProvider
from tests.fakes.clock import FixedClock
from tests.integration.llm.mock_api import ScriptedApi, message
from tests.unit.generation.builders import CONTENT, REQUEST

ANSWER = json.dumps(
    {
        "citation_form": CONTENT.citation_form,
        "shortened_sentence": CONTENT.shortened_sentence,
        "verbal_rewrite": CONTENT.verbal_rewrite,
        "translation": CONTENT.translation,
        "meaning": CONTENT.meaning,
    },
    ensure_ascii=False,
)


@pytest.fixture
def uow() -> Iterator[SqliteUnitOfWork]:
    unit_of_work = SqliteUnitOfWork(open_database(MEMORY))
    yield unit_of_work
    unit_of_work.close()


def _wired(api: ScriptedApi, uow: SqliteUnitOfWork) -> LLMProvider:
    return CachingProvider(CheckedProvider(api.provider()), uow, FixedClock())


def test_second_identical_request_makes_no_http_call(uow: SqliteUnitOfWork) -> None:
    api = ScriptedApi([message(ANSWER)])
    provider = _wired(api, uow)

    first = provider.generate(REQUEST)
    second = provider.generate(REQUEST)

    assert first == CONTENT
    assert second == CONTENT
    assert len(api.requests) == 1


def test_answer_failing_the_checks_is_asked_again(uow: SqliteUnitOfWork) -> None:
    unchecked = json.loads(ANSWER) | {"citation_form": "einen Beschluss fassen"}
    api = ScriptedApi([message(json.dumps(unchecked)), message(ANSWER)])
    provider = _wired(api, uow)

    with pytest.raises(GenerationError):
        provider.generate(REQUEST)
    result = provider.generate(REQUEST)

    assert result == CONTENT
    assert len(api.requests) == 2

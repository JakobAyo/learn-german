"""CachingProvider: hit, miss, and a new key for each key component (0004, 0036)."""

import json
from dataclasses import asdict

import pytest

from learn_german.adapters.storage.sqlite import SqliteUnitOfWork
from learn_german.application.generation import CachingProvider, CheckedProvider, cache_key
from learn_german.application.generation.caching import decode_content, encode_content
from learn_german.domain.errors import GenerationError
from learn_german.domain.models import CardRequest, ChunkKey, ChunkKind
from learn_german.ports import LLMProvider
from tests.fakes.clock import FixedClock
from tests.fakes.llm import FakeProvider, content_for
from tests.unit.generation.builders import CONTENT, REQUEST, content, request


def _key(provider: LLMProvider, req: CardRequest = REQUEST) -> str:
    return cache_key(
        provider=provider.name,
        model=provider.model,
        prompt_version=provider.prompt_version,
        request=req,
    )


def test_cache_key_is_stable() -> None:
    # Pinned: a change to the canonical form silently drops every cached answer.
    pinned = CardRequest(
        ChunkKey("verfügung|zu|stellen"), ChunkKind.NVV, "Sie stellt Geld zur Verfügung.", "", "en"
    )

    key = cache_key(provider="anthropic", model="m", prompt_version="v1", request=pinned)

    assert key == "ba07b5cf9ac48bedb2c94f5f926f32c209533eda82070f607b9faa48db68c57c"


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"provider": "deepseek"}, id="provider"),
        pytest.param({"model": "other-model"}, id="model"),
        pytest.param({"prompt_version": "v2"}, id="prompt-version"),
        pytest.param({"request": request(key=ChunkKey("rolle|spielen"))}, id="chunk-key"),
        pytest.param({"request": request(sentence="Ein anderer Satz.")}, id="sentence"),
        pytest.param({"request": request(context="Anderer Kontext.")}, id="context"),
        pytest.param({"request": request(hint_language="fr")}, id="hint-language"),
    ],
)
def test_cache_key_changes_with_each_component(changes: dict[str, object]) -> None:
    base: dict[str, object] = {
        "provider": "anthropic",
        "model": "m",
        "prompt_version": "v1",
        "request": REQUEST,
    }

    assert cache_key(**{**base, **changes}) != cache_key(**base)  # type: ignore[arg-type]


def test_miss_calls_the_provider_and_stores_the_content(uow: SqliteUnitOfWork) -> None:
    fake = FakeProvider()
    provider = CachingProvider(fake, uow, FixedClock())

    result = provider.generate(REQUEST)

    assert result == content_for(REQUEST)
    assert fake.requests == [REQUEST]
    assert uow.llm_cache.get(_key(fake)) == encode_content(result)


def test_hit_answers_without_calling_the_provider(uow: SqliteUnitOfWork) -> None:
    fake = FakeProvider()
    provider = CachingProvider(fake, uow, FixedClock())
    first = provider.generate(REQUEST)

    second = provider.generate(REQUEST)

    assert second == first
    assert len(fake.requests) == 1


def test_hit_survives_a_new_decorator_on_the_same_database(uow: SqliteUnitOfWork) -> None:
    CachingProvider(FakeProvider(), uow, FixedClock()).generate(REQUEST)
    later = FakeProvider()

    CachingProvider(later, uow, FixedClock()).generate(REQUEST)

    assert later.requests == []


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(FakeProvider("a"), FakeProvider("b"), id="provider"),
        pytest.param(FakeProvider(model="m1"), FakeProvider(model="m2"), id="model"),
        pytest.param(
            FakeProvider(prompt_version="v1"), FakeProvider(prompt_version="v2"), id="prompt"
        ),
    ],
)
def test_provider_identity_change_is_a_miss(
    uow: SqliteUnitOfWork, first: FakeProvider, second: FakeProvider
) -> None:
    CachingProvider(first, uow, FixedClock()).generate(REQUEST)

    CachingProvider(second, uow, FixedClock()).generate(REQUEST)

    assert second.requests == [REQUEST]


@pytest.mark.parametrize(
    "changed",
    [
        pytest.param(request(sentence="Der Rat traf eine Entscheidung."), id="sentence"),
        pytest.param(request(context="Anderer Kontext."), id="context"),
        pytest.param(request(hint_language="fr"), id="hint-language"),
        pytest.param(request(key=ChunkKey("beschluss|fassen")), id="chunk-key"),
    ],
)
def test_request_change_is_a_miss(uow: SqliteUnitOfWork, changed: CardRequest) -> None:
    fake = FakeProvider()
    provider = CachingProvider(fake, uow, FixedClock())
    provider.generate(REQUEST)

    provider.generate(changed)

    assert fake.requests == [REQUEST, changed]


def test_failure_is_not_cached(uow: SqliteUnitOfWork) -> None:
    fake = FakeProvider()
    fake.fail.add(REQUEST.key)
    provider = CachingProvider(fake, uow, FixedClock())

    with pytest.raises(GenerationError):
        provider.generate(REQUEST)

    assert uow.llm_cache.get(_key(fake)) is None


def test_content_failing_the_checks_is_not_cached(uow: SqliteUnitOfWork) -> None:
    fake = FakeProvider()
    fake.responses[REQUEST.key] = content(meaning="a\nb")
    provider = CachingProvider(CheckedProvider(fake), uow, FixedClock())

    with pytest.raises(GenerationError):
        provider.generate(REQUEST)

    assert uow.llm_cache.get(_key(fake)) is None


def test_unreadable_entry_is_a_miss_and_is_replaced(uow: SqliteUnitOfWork) -> None:
    fake = FakeProvider()
    clock = FixedClock()
    with uow:
        uow.llm_cache.put(
            _key(fake),
            '{"citation_form": "old"}',
            provider=fake.name,
            model=fake.model,
            prompt_version=fake.prompt_version,
            created_at=clock.now(),
        )

    result = CachingProvider(fake, uow, clock).generate(REQUEST)

    assert fake.requests == [REQUEST]
    assert uow.llm_cache.get(_key(fake)) == encode_content(result)


def test_decorator_passes_identity_through(uow: SqliteUnitOfWork) -> None:
    provider: LLMProvider = CachingProvider(FakeProvider("p", "m", "v9"), uow, FixedClock())

    assert (provider.name, provider.model, provider.prompt_version) == ("p", "m", "v9")


def test_encoded_content_round_trips() -> None:
    assert decode_content(encode_content(CONTENT)) == CONTENT


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("not json", id="not-json"),
        pytest.param("[]", id="not-an-object"),
        pytest.param('{"citation_form": "x"}', id="missing-fields"),
        pytest.param(encode_content(CONTENT)[:-1] + ', "extra": "x"}', id="extra-field"),
    ],
)
def test_decode_content_rejects_other_shapes(text: str) -> None:
    assert decode_content(text) is None


def test_non_string_field_is_rejected() -> None:
    data = {**asdict(CONTENT), "meaning": 1}

    assert decode_content(json.dumps(data)) is None

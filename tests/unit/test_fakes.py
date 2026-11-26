"""The shared fakes satisfy their ports, checked by mypy through the annotated assignments."""

import pytest

from learn_german.domain.errors import (
    AnkiUnavailableError,
    GenerationError,
    PushError,
    SourceFetchError,
)
from learn_german.domain.models import (
    CHUNK_KEY_FIELD,
    Candidate,
    CardRequest,
    ChunkKey,
    ChunkKind,
    NoteDraft,
    NoteKind,
)
from learn_german.ports import AnkiGateway, ChunkExtractor, LLMProvider, SourceAdapter
from tests.fakes.anki import FakeAnkiGateway
from tests.fakes.extractors import FakeExtractor
from tests.fakes.llm import FakeProvider
from tests.fakes.sources import FakeSource

KEY = ChunkKey("entscheidung|treffen")


def _draft(note_kind: NoteKind = NoteKind.TRANSFORMATION) -> NoteDraft:
    return NoteDraft(note_kind, KEY, ((CHUNK_KEY_FIELD, KEY.value),), ("learn-german",))


def test_fake_anki_gateway_tracks_keys_per_note_kind() -> None:
    gateway: AnkiGateway = FakeAnkiGateway()

    gateway.add_notes([_draft()])

    assert gateway.existing_keys(NoteKind.TRANSFORMATION) == {KEY}
    assert gateway.existing_keys(NoteKind.TRANSLATION) == frozenset()


def test_fake_anki_gateway_rejects_duplicates_and_can_be_down() -> None:
    gateway = FakeAnkiGateway(existing=[(NoteKind.TRANSFORMATION, KEY)])

    with pytest.raises(PushError):
        gateway.add_notes([_draft()])
    gateway.unavailable = True
    with pytest.raises(AnkiUnavailableError):
        gateway.ensure_setup()


def test_fake_provider_records_requests_and_can_fail() -> None:
    fake = FakeProvider()
    provider: LLMProvider = fake
    request = CardRequest(KEY, ChunkKind.NVV, "Sie traf eine Entscheidung.", "", "en")

    content = provider.generate(request)
    fake.fail.add(KEY)

    assert content.citation_form == "entscheidung treffen"
    assert fake.requests == [request]
    with pytest.raises(GenerationError):
        provider.generate(request)


def test_fake_extractor_finds_trigger_words_with_context() -> None:
    extractor: ChunkExtractor = FakeExtractor()

    found = extractor.extract("Es regnete. Der Rat traf eine Entscheidung. Dann war Ruhe.")

    assert found == [
        Candidate(
            KEY,
            ChunkKind.NVV,
            "Der Rat traf eine Entscheidung.",
            "Es regnete. Der Rat traf eine Entscheidung. Dann war Ruhe.",
        )
    ]


def test_fake_source_serves_texts_and_can_fail() -> None:
    fake = FakeSource({"fake:a": "Ein Text."})
    adapter: SourceAdapter = fake
    fake.fail["fake:b"] = "blocked"

    assert adapter.fetch("fake:a").text == "Ein Text."
    with pytest.raises(SourceFetchError, match="blocked"):
        adapter.fetch("fake:b")
    assert fake.fetched == ["fake:a", "fake:b"]

from learn_german.adapters.nlp import NvvExtractor
from learn_german.bootstrap import extractor_registry
from learn_german.domain.models import ChunkKind


def test_extractor_registry_maps_each_kind_name_to_its_extractor() -> None:
    registry = extractor_registry()

    assert set(registry) == {kind.value for kind in ChunkKind}
    assert isinstance(registry["nvv"], NvvExtractor)
    assert registry["nvv"].kind is ChunkKind.NVV

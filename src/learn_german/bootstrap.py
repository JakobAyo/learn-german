"""Composition root: reads settings and wires adapters into use cases. Filled in from M3 on."""

from learn_german.adapters.nlp import NvvExtractor
from learn_german.domain.models import ChunkKind
from learn_german.ports import ChunkExtractor


def extractor_registry() -> dict[str, ChunkExtractor]:
    """Chunk extractors by name (R9). Cheap to build: the spaCy model loads on first use."""
    return {ChunkKind.NVV.value: NvvExtractor.default()}

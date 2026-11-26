"""Fixtures for the `nlp` tests, which need the real spaCy model (`uv sync --extra model`)."""

import pytest

from learn_german.adapters.nlp import NvvExtractor


@pytest.fixture(scope="session")
def nvv_extractor() -> NvvExtractor:
    """One extractor for the session, so the 500 MB model loads once."""
    return NvvExtractor.default()

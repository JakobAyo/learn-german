"""Errors of the LLM adapters, as subclasses of the domain errors (0026)."""

from learn_german.domain.errors import FatalError, ItemError


class LLMAccessError(FatalError):
    """The provider refused the key, the account or the model, so every call would fail."""


class LLMRequestError(ItemError):
    """One call failed after the client's retries: rate limit, server error or network."""

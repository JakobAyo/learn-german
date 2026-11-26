"""Generation decorators around any `LLMProvider`: sanity checks and the response cache.

Wire them as `CachingProvider(CheckedProvider(provider), uow, clock)`, so only content that
passed the checks is cached (0036).
"""

from learn_german.application.generation.caching import CachingProvider, cache_key
from learn_german.application.generation.checks import CheckedProvider, check_card

__all__ = ["CachingProvider", "CheckedProvider", "cache_key", "check_card"]

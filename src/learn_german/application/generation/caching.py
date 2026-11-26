"""`CachingProvider`: an identical request is never paid for twice (0004, 0036)."""

import hashlib
import json
import logging
from dataclasses import asdict, fields

from learn_german.domain.models import CardContent, CardRequest
from learn_german.ports import Clock, LLMProvider, UnitOfWork

logger = logging.getLogger(__name__)

_CONTENT_FIELDS = tuple(field.name for field in fields(CardContent))


def cache_key(*, provider: str, model: str, prompt_version: str, request: CardRequest) -> str:
    """SHA-256 of provider, model, prompt version and the request in canonical JSON.

    Canonical means sorted keys and no extra whitespace, so equal inputs give equal keys
    whatever the order the fields were written in.
    """
    payload = {
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "request": {
            "key": request.key.value,
            "kind": request.kind.value,
            "sentence": request.sentence,
            "context": request.context,
            "hint_language": request.hint_language,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def encode_content(content: CardContent) -> str:
    """The content as the JSON text stored in the cache."""
    return json.dumps(asdict(content), sort_keys=True, ensure_ascii=False)


def decode_content(text: str) -> CardContent | None:
    """Content from a cache entry, or None if the entry does not hold exactly its fields."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or sorted(data) != sorted(_CONTENT_FIELDS):
        return None
    if not all(isinstance(data[name], str) for name in _CONTENT_FIELDS):
        return None
    return CardContent(**{name: data[name] for name in _CONTENT_FIELDS})


class CachingProvider:
    """Decorator that answers from the `llm_cache` table and stores what the inner provider
    returns (0036). Works for any `LLMProvider`.

    Reads and writes run in their own short unit-of-work blocks, so a later failure of the
    chunk (a rejected push) does not roll the paid answer back, and the database is not held
    during the call. Call `generate` outside any `with uow:` block. An entry that no longer
    decodes is treated as a miss and overwritten. Raises what the inner provider raises, and
    `DatabaseError` if the cache cannot be read or written.
    """

    def __init__(self, inner: LLMProvider, uow: UnitOfWork, clock: Clock) -> None:
        self._inner = inner
        self._uow = uow
        self._clock = clock

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model(self) -> str:
        return self._inner.model

    @property
    def prompt_version(self) -> str:
        return self._inner.prompt_version

    def generate(self, request: CardRequest) -> CardContent:
        key = cache_key(
            provider=self.name,
            model=self.model,
            prompt_version=self.prompt_version,
            request=request,
        )
        with self._uow:
            cached = self._uow.llm_cache.get(key)
        if cached is not None:
            content = decode_content(cached)
            if content is not None:
                logger.debug("LLM cache hit for %s", request.key)
                return content
            logger.warning("Ignoring an unreadable LLM cache entry for %s", request.key)
        logger.debug("LLM cache miss for %s; asking %s", request.key, self.name)
        content = self._inner.generate(request)
        with self._uow:
            self._uow.llm_cache.put(
                key,
                encode_content(content),
                provider=self.name,
                model=self.model,
                prompt_version=self.prompt_version,
                created_at=self._clock.now(),
            )
        return content

"""`LocalFileSource`: UTF-8 `.txt` files, the fallback for pages that cannot be fetched (0013)."""

from pathlib import Path

from learn_german.adapters.sources.text import content_hash, normalise_text
from learn_german.domain.errors import SourceFetchError
from learn_german.domain.models import Source, SourceKind
from learn_german.ports import Clock

SUFFIXES = frozenset({".txt"})


class LocalFileSource:
    """Implements `ports.SourceAdapter` for local `.txt` files in UTF-8 (R4).

    Handles any reference that is not a URL and ends in `.txt`. The source's ref is the
    absolute path, so the same file added from another directory is still recognised (R6).
    Its title is the file name without the suffix. Raises `SourceFetchError` when the file
    is missing or unreadable, is not UTF-8, or holds no text.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def can_handle(self, ref: str) -> bool:
        return "://" not in ref and Path(ref).suffix.lower() in SUFFIXES

    def fetch(self, ref: str) -> Source:
        path = Path(ref).expanduser().resolve()
        text = normalise_text(_read_utf8(path))
        if not text:
            raise SourceFetchError(f"{path} holds no text. Put the article text in it first.")
        return Source(
            ref=str(path),
            kind=SourceKind.LOCAL_FILE,
            title=path.stem,
            fetched_at=self._clock.now(),
            content_hash=content_hash(text),
            text=text,
        )


def _read_utf8(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise SourceFetchError(f"{path} does not exist. Check the path.") from exc
    except OSError as exc:
        raise SourceFetchError(
            f"Cannot read {path}: {exc.strerror or exc}. Check that it is a file you may read."
        ) from exc
    try:
        # utf-8-sig drops the byte-order mark some Windows editors write.
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceFetchError(
            f"{path} is not UTF-8 text (invalid byte at position {exc.start}). Save it again "
            "with UTF-8 encoding and add it once more."
        ) from exc

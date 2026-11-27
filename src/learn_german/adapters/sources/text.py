"""Normalising source text and hashing it, shared by every source adapter (R6)."""

import hashlib
import re
import unicodedata

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
PARAGRAPH_SEPARATOR = "\n\n"


def normalise_text(text: str) -> str:
    """NFC text with one blank line between paragraphs and single spaces inside them.

    A blank line separates paragraphs; any other run of whitespace, line breaks included,
    becomes one space. So the same text saved with other line wrapping, indentation or
    composed umlauts normalises to the same string and gets the same hash.
    """
    composed = unicodedata.normalize("NFC", text)
    paragraphs = (" ".join(raw.split()) for raw in _PARAGRAPH_BREAK.split(composed))
    return PARAGRAPH_SEPARATOR.join(p for p in paragraphs if p)


def content_hash(normalised: str) -> str:
    """SHA-256 of the normalised text, as lowercase hex."""
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(text.split())

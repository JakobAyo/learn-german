"""The light-verb list and spelling-variant table, read from data files in the package."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib.resources import files
from types import MappingProxyType
from typing import Self

_DATA = files("learn_german.adapters.nlp").joinpath("data")
LIGHT_VERBS_FILE = "light_verbs.txt"
SPELLING_VARIANTS_FILE = "spelling_variants.tsv"


@dataclass(frozen=True, slots=True)
class SpellingVariant:
    """The separate form of a one-word spelling: *infrage* is noun `frage`, preposition `in`."""

    noun: str
    preposition: str


@dataclass(frozen=True, slots=True)
class Lexicon:
    """Word lists the matcher and key builder need (0011, 0016)."""

    light_verbs: frozenset[str]
    """Infinitives, with a separable prefix where the verb has one (0030)."""
    spelling_variants: Mapping[str, SpellingVariant]
    """Lowercase one-word form to its separate form."""

    @classmethod
    def load(cls) -> Self:
        """Read both data files shipped with the package. Raises ValueError if one is malformed."""
        light_verbs = _DATA.joinpath(LIGHT_VERBS_FILE).read_text(encoding="utf-8")
        variants = _DATA.joinpath(SPELLING_VARIANTS_FILE).read_text(encoding="utf-8")
        return cls(read_light_verbs(light_verbs), read_spelling_variants(variants))


def read_light_verbs(content: str) -> frozenset[str]:
    """One infinitive per line; blank lines and `#` comments are skipped."""
    return frozenset(_data_lines(content))


def read_spelling_variants(content: str) -> Mapping[str, SpellingVariant]:
    """Tab-separated lines of one-word form, noun and preposition. Raises ValueError otherwise."""
    variants: dict[str, SpellingVariant] = {}
    for line in _data_lines(content):
        columns = line.split("\t")
        if len(columns) != 3 or not all(columns):
            raise ValueError(f"spelling variant line {line!r} needs three tab-separated columns")
        word, noun, preposition = columns
        variants[word] = SpellingVariant(noun, preposition)
    return MappingProxyType(variants)


def _data_lines(content: str) -> Iterator[str]:
    for raw in content.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            yield line

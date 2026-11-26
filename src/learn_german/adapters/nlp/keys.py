"""Turn a matched NVV into its permanent chunk key (0011). Pure: no spaCy."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from learn_german.adapters.nlp.lexicon import SpellingVariant
from learn_german.adapters.nlp.tokens import TokenView
from learn_german.domain.models import ChunkKey

logger = logging.getLogger(__name__)

# 0011: contractions are expanded (zur -> zu, im -> in).
CONTRACTIONS: Mapping[str, str] = {
    "am": "an", "ans": "an", "aufs": "auf", "beim": "bei", "durchs": "durch",
    "fürs": "für", "hinterm": "hinter", "hinters": "hinter", "im": "in", "ins": "in",
    "übers": "über", "überm": "über", "ums": "um", "unterm": "unter", "unters": "unter",
    "vom": "von", "vorm": "vor", "vors": "vor", "zum": "zu", "zur": "zu",
}  # fmt: skip


@dataclass(frozen=True, slots=True)
class NvvMatch:
    """The tokens of one Nomen-Verb-Verbindung in a sentence, as the matcher found them.

    `nominal` is the noun, or a one-word spelling such as *infrage* that stands for both
    preposition and noun. Articles, adjectives and negation are not part of a match (0011).
    """

    verb: TokenView
    nominal: TokenView
    preposition: TokenView | None = None
    particle: TokenView | None = None
    """The verb's own separable prefix (*nahm … auf*), if it has one (0030)."""
    reflexive: bool = False


def verb_infinitive(verb: TokenView, particle: TokenView | None) -> str:
    """The verb's lowercase infinitive, with its own separable prefix in front (0030)."""
    lemma = verb.lemma.lower()
    if particle is None:
        return lemma
    prefix = particle.text.lower()
    return lemma if lemma.startswith(prefix) else prefix + lemma


def preposition_lemma(token: TokenView) -> str:
    """The lowercase preposition, with a contraction expanded (0011)."""
    text = token.text.lower()
    return CONTRACTIONS.get(text, text)


def build_key(match: NvvMatch, variants: Mapping[str, SpellingVariant]) -> ChunkKey | None:
    """The 0011 key of a match, or None when a lemma is not a valid key part (digits, …)."""
    variant = variants.get(match.nominal.text.lower())
    preposition: str | None
    if variant is not None:
        noun, preposition = variant.noun, variant.preposition
    else:
        noun = (match.nominal.lemma or match.nominal.text).lower()
        preposition = None if match.preposition is None else preposition_lemma(match.preposition)
    verb = verb_infinitive(match.verb, match.particle)
    try:
        return ChunkKey.from_parts(noun, verb, preposition=preposition, reflexive=match.reflexive)
    except ValueError:
        logger.debug("Skipping NVV with lemmas %r %r %r", noun, preposition, verb)
        return None

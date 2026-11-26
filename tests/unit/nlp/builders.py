"""Hand-built parses for unit tests, written in the column order spaCy prints them."""

from learn_german.adapters.nlp.keys import NvvMatch
from learn_german.adapters.nlp.lexicon import Lexicon, SpellingVariant
from learn_german.adapters.nlp.tokens import ParsedSentence, TokenView

LEXICON = Lexicon(
    light_verbs=frozenset(
        {
            "aufnehmen",
            "erheben",
            "geben",
            "gehen",
            "kommen",
            "legen",
            "nehmen",
            "spielen",
            "stehen",
            "stellen",
            "treffen",
            "ziehen",
        }
    ),
    spelling_variants={
        "infrage": SpellingVariant("frage", "in"),
        "zustande": SpellingVariant("stand", "zu"),
    },
)


def token(row: str, index: int = 0) -> TokenView:
    """One token from `text lemma POS TAG dep head [morph]`."""
    text, lemma, pos, tag, dep, head, *morph = row.split()
    return TokenView(index, text, lemma, pos, tag, dep, int(head), "".join(morph))


def parsed(*rows: str) -> ParsedSentence:
    """A sentence from one row per token, as `token` reads them."""
    tokens = tuple(token(row, index) for index, row in enumerate(rows))
    for t in tokens:
        # Catch miscounted heads: only the root points at itself, and heads stay in range.
        if (t.dep == "ROOT") != (t.head == t.index) or not 0 <= t.head < len(tokens):
            raise ValueError(f"token {t.index} {t.text!r} has a bad head {t.head}")
    return ParsedSentence(" ".join(t.text for t in tokens), tokens)


def nvv(
    noun: str,
    verb: str,
    *,
    preposition: str | None = None,
    particle: str | None = None,
    reflexive: bool = False,
) -> NvvMatch:
    """A match from token rows, for key-builder tests that skip the matcher."""
    return NvvMatch(
        verb=token(verb),
        nominal=token(noun),
        preposition=None if preposition is None else token(preposition),
        particle=None if particle is None else token(particle),
        reflexive=reflexive,
    )

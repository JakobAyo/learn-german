"""spaCy-free view of a parsed sentence, so matching and keys are testable without the model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenView:
    """One token of a parsed sentence, holding only what the matcher and key builder read.

    Labels follow the German spaCy models: `pos` is the universal tag (NOUN, VERB, ADP),
    `tag` the STTS tag (APPRART, PTKVZ, PRF, VVPP) and `dep` the TIGER label (oa, cvc, svp).
    """

    index: int
    """Position in its sentence, from 0."""
    text: str
    lemma: str
    pos: str
    tag: str
    dep: str
    head: int
    """Index of the head in the same sentence. The root points at itself."""
    morph: str = ""
    """Morphological features as spaCy writes them, for example `Case=Dat|Number=Plur`."""

    @property
    def is_plural(self) -> bool:
        return "Number=Plur" in self.morph.split("|")


@dataclass(frozen=True, slots=True)
class ParsedSentence:
    """A sentence with whitespace collapsed and its tokens in text order."""

    text: str
    tokens: tuple[TokenView, ...]

    def children(self, token: TokenView) -> list[TokenView]:
        """Tokens whose head is `token`, in text order."""
        return [t for t in self.tokens if t.head == token.index and t.index != token.index]

    def head_of(self, token: TokenView) -> TokenView | None:
        """The token's head, or None for the root."""
        return None if token.head == token.index else self.tokens[token.head]

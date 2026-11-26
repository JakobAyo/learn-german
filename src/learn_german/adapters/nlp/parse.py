"""Parse German text with spaCy and hand the rest of the extractor plain `TokenView`s."""

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from learn_german.adapters.nlp.tokens import ParsedSentence, TokenView
from learn_german.domain.errors import NlpModelMissingError

if TYPE_CHECKING:
    from spacy.language import Language
    from spacy.tokens import Doc, Span

MODEL_NAME = "de_core_news_lg"
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def load_spacy_model(name: str) -> "Language":
    """`spacy.load`, imported on first use so commands that never parse start quickly."""
    import spacy

    return spacy.load(name)


class SpacyParser:
    """Splits text into parsed sentences with a spaCy model.

    The model loads once, on the first call to `parse`. Paragraphs are batched through
    `nlp.pipe`. Raises `NlpModelMissingError` when the model is not installed (0027).
    """

    def __init__(
        self,
        model: str = MODEL_NAME,
        *,
        loader: Callable[[str], "Language"] = load_spacy_model,
        batch_size: int = 32,
    ) -> None:
        self._model = model
        self._loader = loader
        self._batch_size = batch_size
        self._nlp: Language | None = None

    def parse(self, text: str) -> list[ParsedSentence]:
        """The text's sentences in order, each with its tokens."""
        nlp = self._load()
        sentences: list[ParsedSentence] = []
        for doc in nlp.pipe(paragraphs(text), batch_size=self._batch_size):
            sentences += doc_sentences(doc)
        return sentences

    def _load(self) -> "Language":
        if self._nlp is None:
            try:
                self._nlp = self._loader(self._model)
            except OSError as exc:
                raise NlpModelMissingError(
                    f"The spaCy model {self._model} is not installed. Install learn-german "
                    "with the model extra (learn-german[model]), or run `uv sync --extra model` "
                    "in a development checkout."
                ) from exc
        return self._nlp


def paragraphs(text: str) -> list[str]:
    """Paragraphs split at blank lines, with line breaks and runs of spaces collapsed."""
    return [p for raw in _PARAGRAPH_BREAK.split(text) if (p := " ".join(raw.split()))]


def doc_sentences(doc: "Doc") -> list[ParsedSentence]:
    """Convert a parsed spaCy `Doc` into sentences of `TokenView`s, dropping empty ones."""
    return [_sentence(span) for span in doc.sents if span.text.strip()]


def _sentence(span: "Span") -> ParsedSentence:
    start = span.start
    tokens = tuple(
        TokenView(
            index=token.i - start,
            text=token.text,
            lemma=token.lemma_,
            pos=token.pos_,
            tag=token.tag_,
            dep=token.dep_,
            head=token.head.i - start,
            morph=str(token.morph),
        )
        for token in span
    )
    return ParsedSentence(span.text.strip(), tokens)

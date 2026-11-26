"""Requests and card content for generation tests. German is hand-written (R28)."""

from dataclasses import replace

from learn_german.domain.models import CardContent, CardRequest, ChunkKey, ChunkKind

DECISION = ChunkKey("entscheidung|treffen")

LONG_SENTENCE = (
    "Nach einer langen Sitzung am Montagabend hat der Stadtrat endlich eine Entscheidung "
    "über den Bau der neuen Brücke getroffen, die seit Jahren umstritten ist."
)
CONTEXT = (
    "Die Brücke soll den Hafen mit der Altstadt verbinden. " + LONG_SENTENCE + " "
    "Die Bauarbeiten sollen im Frühjahr beginnen."
)

REQUEST = CardRequest(DECISION, ChunkKind.NVV, LONG_SENTENCE, CONTEXT, "en")

CONTENT = CardContent(
    citation_form="eine Entscheidung treffen",
    shortened_sentence=(
        "Der Stadtrat hat endlich eine Entscheidung über den Bau der neuen Brücke getroffen."
    ),
    verbal_rewrite="Der Stadtrat hat endlich über den Bau der neuen Brücke entschieden.",
    translation="The city council has finally made a decision on building the new bridge.",
    meaning="eine Entscheidung treffen = entscheiden, sich festlegen",
)


def request(
    *,
    key: ChunkKey = DECISION,
    sentence: str = LONG_SENTENCE,
    context: str = CONTEXT,
    hint_language: str = "en",
) -> CardRequest:
    return CardRequest(key, ChunkKind.NVV, sentence, context, hint_language)


def content(**changes: str) -> CardContent:
    return replace(CONTENT, **changes)

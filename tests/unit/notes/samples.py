"""Card content and requests for note tests. German is hand-written (R28)."""

from learn_german.domain.models import CardContent, CardRequest, ChunkKey, ChunkKind, RunId

DECISION = ChunkKey("entscheidung|treffen")
DISPOSAL = ChunkKey("verfügung|zu|stellen")
RUN = RunId("run-20261124-1530")

REQUEST = CardRequest(
    key=DECISION,
    kind=ChunkKind.NVV,
    sentence="Nach langer Sitzung hat der Stadtrat am Montag eine Entscheidung getroffen.",
    context="Die Brücke ist umstritten. Nach langer Sitzung hat der Stadtrat entschieden.",
    hint_language="en",
)

CONTENT = CardContent(
    citation_form="eine Entscheidung treffen",
    shortened_sentence="Der Stadtrat hat am Montag eine Entscheidung über die Brücke getroffen.",
    verbal_rewrite="Der Stadtrat hat am Montag über die Brücke entschieden.",
    translation="The city council made a decision about the bridge on Monday.",
    meaning="eine Entscheidung treffen = entscheiden, sich festlegen",
)

DISPOSAL_REQUEST = CardRequest(
    key=DISPOSAL,
    kind=ChunkKind.NVV,
    sentence="Die Stadt stellt den Vereinen ab Mai neue Räume zur Verfügung.",
    context="Die Stadt stellt den Vereinen ab Mai neue Räume zur Verfügung.",
    hint_language="en",
)

DISPOSAL_CONTENT = CardContent(
    citation_form="zur Verfügung stellen",
    shortened_sentence="Die Stadt stellt den Vereinen ab Mai neue Räume zur Verfügung.",
    verbal_rewrite="Die Stadt gibt den Vereinen ab Mai neue Räume.",
    translation="From May, the city is providing the clubs with new rooms.",
    meaning="zur Verfügung stellen = bereitstellen, geben",
)

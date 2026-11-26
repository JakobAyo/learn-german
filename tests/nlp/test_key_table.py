"""Every row of the 0011 key table, found by the real model in hard word orders."""

import pytest

from learn_german.adapters.nlp import NvvExtractor

pytestmark = pytest.mark.nlp

# (0011 row, sentence, expected key). Each row appears with a separated verb, the perfect
# tense, a subordinate clause and negation, where the chunk allows it.
CASES = [
    (
        "zur Verfügung stellen",
        "Die Stadt stellte den Vereinen ihre Hallen kostenlos zur Verfügung.",
        "verfügung|zu|stellen",
    ),
    (
        "zur Verfügung stellen",
        "Die Stadt hat den Vereinen ihre Hallen zur Verfügung gestellt.",
        "verfügung|zu|stellen",
    ),
    (
        "zur Verfügung stellen",
        "Wir freuen uns, dass die Stadt ihre Hallen zur Verfügung stellt.",
        "verfügung|zu|stellen",
    ),
    (
        "zur Verfügung stellen",
        "Die Stadt stellt ihre Hallen nicht mehr zur Verfügung.",
        "verfügung|zu|stellen",
    ),
    (
        "zur Verfügung stehen",
        "Die Räume stehen allen Gästen den ganzen Tag zur Verfügung.",
        "verfügung|zu|stehen",
    ),
    (
        "zur Verfügung stehen",
        "Die Räume haben den Gästen leider nicht zur Verfügung gestanden.",
        "verfügung|zu|stehen",
    ),
    (
        "zur Verfügung stehen",
        "Ich weiß nicht, ob der Saal morgen zur Verfügung steht.",
        "verfügung|zu|stehen",
    ),
    ("in Frage stellen", "Er stellt die Ergebnisse der Studie in Frage.", "frage|in|stellen"),
    ("in Frage stellen", "Sie hat seine Ideen nie in Frage gestellt.", "frage|in|stellen"),
    (
        "in Frage stellen",
        "Es überrascht, dass niemand die Ergebnisse in Frage stellt.",
        "frage|in|stellen",
    ),
    ("in Frage stellen", "Die Forscher stellen die Methode nicht in Frage.", "frage|in|stellen"),
    (
        "infrage stellen",
        "Die Opposition stellt die Zahlen der Regierung infrage.",
        "frage|in|stellen",
    ),
    ("infrage stellen", "Er wollte die Ergebnisse nicht infrage stellen.", "frage|in|stellen"),
    (
        "eine Frage stellen",
        "Die Studentin stellte dem Professor eine kluge Frage.",
        "frage|stellen",
    ),
    ("eine Frage stellen", "Der Journalist hat dem Minister eine Frage gestellt.", "frage|stellen"),
    ("eine Frage stellen", "Ich wusste nicht, warum er diese Frage stellte.", "frage|stellen"),
    ("eine Frage stellen", "In der Sitzung stellte niemand eine Frage.", "frage|stellen"),
    ("keine Rolle spielen", "Das Geld spielt keine Rolle.", "rolle|spielen"),
    (
        "keine Rolle spielen",
        "Das Wetter hat bei der Entscheidung keine Rolle gespielt.",
        "rolle|spielen",
    ),
    (
        "keine Rolle spielen",
        "Wir fahren trotzdem, weil das Wetter keine Rolle spielt.",
        "rolle|spielen",
    ),
    ("keine Rolle spielen", "Der Preis spielte eine wichtige Rolle.", "rolle|spielen"),
    ("sich in Acht nehmen", "Du musst dich vor dem Hund in Acht nehmen.", "acht|in|sich|nehmen"),
    ("sich in Acht nehmen", "Sie nahm sich vor dem Hund in Acht.", "acht|in|sich|nehmen"),
    ("sich in Acht nehmen", "Er hat sich nicht genug in Acht genommen.", "acht|in|sich|nehmen"),
    (
        "sich in Acht nehmen",
        "Es ist wichtig, dass man sich vor Betrügern in Acht nimmt.",
        "acht|in|sich|nehmen",
    ),
    (
        "traf eine Entscheidung",
        "Der Vorstand traf gestern eine Entscheidung.",
        "entscheidung|treffen",
    ),
    (
        "traf eine Entscheidung",
        "Wir haben noch keine Entscheidung getroffen.",
        "entscheidung|treffen",
    ),
    (
        "traf eine Entscheidung",
        "Wir warten, bis die Regierung eine Entscheidung trifft.",
        "entscheidung|treffen",
    ),
    ("traf eine Entscheidung", "Die Entscheidung wurde gestern getroffen.", "entscheidung|treffen"),
    (
        "traf eine Entscheidung",
        "Eine Entscheidung muss bald getroffen werden.",
        "entscheidung|treffen",
    ),
]


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [(sentence, key) for _, sentence, key in CASES],
    ids=[f"{row}: {sentence}" for row, sentence, _ in CASES],
)
def test_nvv_extractor_finds_0011_key(
    nvv_extractor: NvvExtractor, sentence: str, expected: str
) -> None:
    keys = [candidate.key.value for candidate in nvv_extractor.extract(sentence)]

    assert keys == [expected]

"""The matcher on hand-built parses, copied from what de_core_news_lg returns (0029)."""

from learn_german.adapters.nlp.keys import build_key
from learn_german.adapters.nlp.match import find_matches
from learn_german.adapters.nlp.tokens import ParsedSentence
from tests.unit.nlp.builders import LEXICON, parsed


def keys(sentence: ParsedSentence) -> list[str]:
    matches = find_matches(sentence, LEXICON)
    return [str(build_key(m, LEXICON.spelling_variants)) for m in matches]


def test_find_matches_takes_an_object_with_its_article_dropped() -> None:
    sentence = parsed(
        "Der der DET ART nk 1",
        "Vorstand Vorstand NOUN NN sb 2",
        "traf treffen VERB VVFIN ROOT 2",
        "eine ein DET ART nk 4",
        "Entscheidung Entscheidung NOUN NN oa 2",
    )

    assert keys(sentence) == ["entscheidung|treffen"]


def test_find_matches_drops_negation() -> None:
    sentence = parsed(
        "Das der DET ART nk 1",
        "Geld Geld NOUN NN sb 2",
        "spielt spielen VERB VVFIN ROOT 2",
        "keine kein DET PIAT nk 4",
        "Rolle Rolle NOUN NN oa 2",
    )

    assert keys(sentence) == ["rolle|spielen"]


def test_find_matches_ignores_a_verb_off_the_light_verb_list() -> None:
    sentence = parsed(
        "Sie sie PRON PPER sb 1",
        "lösten lösen VERB VVFIN ROOT 1",
        "das der DET ART nk 3",
        "Problem Problem NOUN NN oa 1",
    )

    assert keys(sentence) == []


def test_find_matches_prefers_a_cvc_phrase_to_the_object() -> None:
    sentence = parsed(
        "Die der DET ART nk 1",
        "Firma Firma NOUN NN sb 2",
        "stellte stellen VERB VVFIN ROOT 2",
        "Laptops Laptop NOUN NN oa 2 Case=Acc|Number=Plur",
        "zur zu ADP APPRART cvc 2",
        "Verfügung Verfügung NOUN NN nk 4",
    )

    assert keys(sentence) == ["verfügung|zu|stellen"]


def test_find_matches_drops_a_complement_phrase_next_to_an_object() -> None:
    # The model labels "auf Vollständigkeit" cvc, but it complements "Anspruch".
    sentence = parsed(
        "Die der DET ART nk 1",
        "Liste Liste NOUN NN sb 2",
        "erhebt erheben VERB VVFIN ROOT 2",
        "keinen kein DET PIAT nk 4",
        "Anspruch Anspruch NOUN NN oa 2",
        "auf auf ADP APPR cvc 2",
        "Vollständigkeit Vollständigkeit NOUN NN nk 5",
    )

    assert keys(sentence) == ["anspruch|erheben"]


def test_find_matches_prefers_a_bare_phrase_to_an_object_with_determiner() -> None:
    sentence = parsed(
        "Wir wir PRON PPER sb 1",
        "ziehen ziehen VERB VVFIN ROOT 1",
        "diese dieser DET PDAT nk 3",
        "Möglichkeit Möglichkeit NOUN NN oa 1",
        "in in ADP APPR mo 1",
        "Betracht Betracht NOUN NN nk 4",
    )

    assert keys(sentence) == ["betracht|in|ziehen"]


def test_find_matches_prefers_a_bare_object_to_a_bare_phrase() -> None:
    sentence = parsed(
        "Er er PRON PPER sb 1",
        "nahm nehmen VERB VVFIN ROOT 1",
        "in in ADP APPR mo 1",
        "Ruhe Ruhe NOUN NN nk 2",
        "Abschied Abschied NOUN NN oa 1",
    )

    assert keys(sentence) == ["abschied|nehmen"]


def test_find_matches_keeps_only_the_last_bare_phrase() -> None:
    sentence = parsed(
        "dass dass SCONJ KOUS cp 7",
        "er er PRON PPER sb 7",
        "sich sich PRON PRF oa 7",
        "in in ADP APPR mo 7",
        "Zukunft Zukunft NOUN NN nk 3",
        "in in ADP APPR mo 7",
        "Acht Acht PROPN NN nk 5",
        "nimmt nehmen VERB VVFIN ROOT 7",
    )

    assert keys(sentence) == ["acht|in|sich|nehmen"]


def test_find_matches_accepts_a_capitalised_numeral_as_noun() -> None:
    sentence = parsed(
        "Sie sie PRON PPER sb 1",
        "nahm nehmen VERB VVFIN ROOT 1",
        "sich sich PRON PRF oa 1",
        "in in ADP APPR mo 1",
        "Acht Acht NUM CARD nk 3",
    )

    assert keys(sentence) == ["acht|in|sich|nehmen"]


def test_find_matches_rejects_a_phrase_with_an_article() -> None:
    sentence = parsed(
        "Die der DET ART nk 1",
        "Kinder Kind NOUN NN sb 2 Number=Plur",
        "gingen gehen VERB VVFIN ROOT 2",
        "in in ADP APPR mo 2",
        "die der DET ART nk 5",
        "Schule Schule NOUN NN nk 3",
    )

    assert keys(sentence) == []


def test_find_matches_rejects_a_contracted_phrase_without_cvc() -> None:
    sentence = parsed(
        "Die der DET ART nk 1",
        "Vase Vase NOUN NN sb 2",
        "stand stehen VERB VVFIN ROOT 2",
        "im in ADP APPRART mo 2",
        "Garten Garten NOUN NN nk 3",
    )

    assert keys(sentence) == []


def test_find_matches_rejects_a_plural_phrase() -> None:
    sentence = parsed(
        "Wir wir PRON PPER sb 1",
        "kommen kommen VERB VVFIN ROOT 1",
        "mit mit ADP APPR mo 1",
        "Freunden Freund NOUN NN nk 2 Case=Dat|Number=Plur",
    )

    assert keys(sentence) == []


def test_find_matches_rejects_a_phrase_with_a_numeral() -> None:
    sentence = parsed(
        "Er er PRON PPER sb 1",
        "kommt kommen VERB VVFIN ROOT 1",
        "um um ADP APPR mo 1",
        "acht acht NUM CARD nk 4",
        "Uhr Uhr NOUN NN nk 2",
    )

    assert keys(sentence) == []


def test_find_matches_rejects_a_phrase_fronted_before_the_finite_verb() -> None:
    sentence = parsed(
        "Nach nach ADP APPR mo 3",
        "langer lang ADJ ADJA nk 2",
        "Diskussion Diskussion NOUN NN nk 0",
        "kam kommen VERB VVFIN ROOT 3",
        "der der DET ART nk 5",
        "Rat Rat NOUN NN sb 3",
    )

    assert keys(sentence) == []


def test_find_matches_takes_the_subject_of_a_passive() -> None:
    sentence = parsed(
        "Die der DET ART nk 1",
        "Entscheidung Entscheidung NOUN NN sb 2",
        "wurde werden AUX VAFIN ROOT 2",
        "gestern gestern ADV ADV mo 4",
        "getroffen treffen VERB VVPP oc 2",
    )

    assert keys(sentence) == ["entscheidung|treffen"]


def test_find_matches_takes_the_subject_of_a_modal_passive() -> None:
    sentence = parsed(
        "Eine ein DET ART nk 1",
        "Entscheidung Entscheidung NOUN NN sb 2",
        "muss müssen AUX VMFIN ROOT 2",
        "bald bald ADV ADV mo 4",
        "getroffen treffen VERB VVPP oc 5",
        "werden werden AUX VAINF oc 2",
    )

    assert keys(sentence) == ["entscheidung|treffen"]


def test_find_matches_ignores_the_subject_of_a_perfect_with_sein() -> None:
    sentence = parsed(
        "Der der DET ART nk 1",
        "Zug Zug NOUN NN sb 2",
        "ist sein AUX VAFIN ROOT 2",
        "gekommen kommen VERB VVPP oc 2",
    )

    assert keys(sentence) == []


def test_find_matches_ignores_a_passive_without_noun_subject() -> None:
    sentence = parsed(
        "Es es PRON PPER sb 1",
        "wurde werden AUX VAFIN ROOT 1",
        "viel viel PRON PIS mo 3",
        "gespielt spielen VERB VVPP oc 1",
    )

    assert keys(sentence) == []


def test_find_matches_joins_a_separated_prefix_to_the_verb() -> None:
    sentence = parsed(
        "Wir wir PRON PPER sb 1",
        "nahmen nehmen VERB VVFIN ROOT 1",
        "Kontakt Kontakt NOUN NN oa 1",
        "mit mit ADP APPR mnr 2",
        "der der DET ART nk 5",
        "Behörde Behörde NOUN NN nk 3",
        "auf auf ADP PTKVZ svp 1",
    )

    assert keys(sentence) == ["kontakt|aufnehmen"]


def test_find_matches_ignores_a_prefixed_verb_off_the_list() -> None:
    sentence = parsed(
        "Die der DET ART nk 1",
        "Polizei Polizei NOUN NN sb 2",
        "nahm nehmen VERB VVFIN ROOT 2",
        "den der DET ART nk 4",
        "Mann Mann NOUN NN oa 2",
        "fest fest ADV PTKVZ svp 2",
    )

    assert keys(sentence) == []


def test_find_matches_skips_existential_es_gibt() -> None:
    sentence = parsed(
        "Es es PRON PPER sb 1",
        "gibt geben VERB VVFIN ROOT 1",
        "keine kein DET PIAT nk 3",
        "Lösung Lösung NOUN NN oa 1",
    )

    assert keys(sentence) == []


def test_find_matches_skips_es_geht_um() -> None:
    sentence = parsed(
        "Es es PRON PPER ep 1",
        "geht gehen VERB VVFIN ROOT 1",
        "um um ADP APPR mo 1",
        "Geld Geld NOUN NN nk 2",
    )

    assert keys(sentence) == []


def test_find_matches_marks_a_dative_reflexive() -> None:
    sentence = parsed(
        "Sie sie PRON PPER sb 1",
        "gab geben VERB VVFIN ROOT 1",
        "sich sich PRON PRF da 1",
        "große groß ADJ ADJA nk 4",
        "Mühe Mühe NOUN NN oa 1",
    )

    assert keys(sentence) == ["mühe|sich|geben"]


def test_find_matches_maps_a_one_word_variant() -> None:
    sentence = parsed(
        "Er er PRON PPER sb 1",
        "stellt stellen VERB VVFIN ROOT 1",
        "die der DET ART nk 3",
        "Pläne Plan NOUN NN oa 1 Number=Plur",
        "infrage infrag ADJ ADJD mo 1",
    )

    assert keys(sentence) == ["frage|in|stellen"]


def test_find_matches_does_not_treat_a_variant_as_a_separable_prefix() -> None:
    sentence = parsed(
        "Der der DET ART nk 1",
        "Vertrag Vertrag NOUN NN sb 2",
        "kam kommen VERB VVFIN ROOT 2",
        "zustande zustande ADV PTKVZ svp 2",
    )

    assert keys(sentence) == ["stand|zu|kommen"]


def test_find_matches_returns_matches_in_verb_order() -> None:
    sentence = parsed(
        "Er er PRON PPER sb 1",
        "stellte stellen VERB VVFIN ROOT 1",
        "eine ein DET ART nk 3",
        "Frage Frage NOUN NN oa 1",
        "und und CCONJ KON cd 1",
        "niemand niemand PRON PIS sb 6",
        "gab geben VERB VVFIN cj 4",
        "eine ein DET ART nk 8",
        "Antwort Antwort NOUN NN oa 6",
    )

    assert keys(sentence) == ["frage|stellen", "antwort|geben"]

"""Find Nomen-Verb-Verbindungen in a parsed sentence (R8, 0029). Pure: no spaCy.

A light verb is a verb whose infinitive, with its own separable prefix, is on the light-verb
list. Each of its dependents that could be the nominal part of an NVV is sorted into a tier,
and only the most NVV-like non-empty tier is kept, so an ordinary object next to a real NVV
(*den Mitarbeitern Laptops zur Verfügung stellen*) does not become a second chunk:

1. a one-word spelling variant (*infrage*) or a PP the parser labels `cvc`
   (collocational verb construction);
2. an accusative object noun without a determiner, *kein* aside (*Rücksicht nehmen*,
   *keinen Wert legen*);
3. the last bare PP: preposition without a contracted article, singular noun without
   determiner or numeral, not fronted before a finite main verb (*in Betracht ziehen*,
   *auf Kritik stoßen*);
4. any other accusative object noun, or the subject of a *werden* passive.

When the verb has an object, a PP whose preposition usually introduces the noun's own
complement (*Wert legen auf*, *Kritik üben an*) is never the NVV, even if labelled `cvc`.
"""

from collections.abc import Callable

from learn_german.adapters.nlp.keys import NvvMatch, preposition_lemma, verb_infinitive
from learn_german.adapters.nlp.lexicon import Lexicon
from learn_german.adapters.nlp.tokens import ParsedSentence, TokenView

_PREPOSITION_TAGS = frozenset({"APPR", "APPRART"})
_CONTRACTED_PREPOSITION = "APPRART"
_FINITE_VERB = "VVFIN"
_COMMON_NOUN = "NN"
_DETERMINER_POS = frozenset({"DET", "NUM"})
_REFLEXIVE_DEPS = frozenset({"oa", "da"})
_NEGATION = "kein"
# Prepositions that, next to an object, introduce the object's complement, not an NVV.
_COMPLEMENT_PREPOSITIONS = frozenset(
    {"an", "auf", "bei", "für", "gegen", "mit", "nach", "über", "von"}
)
_SUBJECT_DEPS = frozenset({"sb", "ep"})
# "es gibt" (there is) and "es geht um" (it is about) are existential, not NVVs.
_EXPLETIVE_VERBS = frozenset({"geben", "gehen"})


def find_matches(sentence: ParsedSentence, lexicon: Lexicon) -> list[NvvMatch]:
    """Every NVV in the sentence, in the text order of their verbs."""
    matches: list[NvvMatch] = []
    for token in sentence.tokens:
        if token.pos == "VERB":
            matches += _matches_for_verb(sentence, token, lexicon)
    return matches


def _matches_for_verb(
    sentence: ParsedSentence, verb: TokenView, lexicon: Lexicon
) -> list[NvvMatch]:
    children = sentence.children(verb)
    variants = lexicon.spelling_variants
    particle = next(
        (c for c in children if c.dep == "svp" and c.text.lower() not in variants), None
    )
    infinitive = verb_infinitive(verb, particle)
    if infinitive not in lexicon.light_verbs:
        return []
    if infinitive in _EXPLETIVE_VERBS and any(_is_expletive(c) for c in children):
        return []
    reflexive = any(c.tag == "PRF" and c.dep in _REFLEXIVE_DEPS for c in children)

    def match(nominal: TokenView, preposition: TokenView | None = None) -> NvvMatch:
        return NvvMatch(verb, nominal, preposition, particle, reflexive)

    objects = _objects(sentence, verb, children)
    phrases = [
        (adp, noun)
        for adp in children
        if (noun := _phrase_noun(sentence, adp))
        and not (objects and preposition_lemma(adp) in _COMPLEMENT_PREPOSITIONS)
    ]
    bare_phrases = [(a, n) for a, n in phrases if _is_bare_phrase(sentence, verb, a, n)]
    tiers: list[list[NvvMatch]] = [
        [match(c) for c in children if c.text.lower() in variants]
        + [match(noun, adp) for adp, noun in phrases if adp.dep == "cvc"],
        [match(noun) for noun in objects if not _has_determiner(sentence, noun, but=_NEGATION)],
        # The NVV's phrase closes the middle field, so only the last bare phrase counts.
        [match(noun, adp) for adp, noun in bare_phrases[-1:]],
        [match(noun) for noun in objects],
    ]
    return next((tier for tier in tiers if tier), [])


def _phrase_noun(sentence: ParsedSentence, adp: TokenView) -> TokenView | None:
    if adp.tag not in _PREPOSITION_TAGS:
        return None
    return _first(sentence.children(adp), lambda c: c.dep == "nk" and _is_noun(c))


def _is_bare_phrase(
    sentence: ParsedSentence, verb: TokenView, adp: TokenView, noun: TokenView
) -> bool:
    # A contracted article (im Garten), a plural (mit Freunden) or a fronted phrase
    # (Nach langer Diskussion traf …) is rarely the nominal part of an NVV.
    if adp.dep == "cvc" or adp.tag == _CONTRACTED_PREPOSITION or noun.is_plural:
        return False
    return not _is_fronted(sentence, verb, adp) and not _has_determiner(sentence, noun)


def _is_fronted(sentence: ParsedSentence, verb: TokenView, adp: TokenView) -> bool:
    """Whether the phrase stands before the finite verb of a main clause (Vorfeld)."""
    if verb.tag != _FINITE_VERB or verb.dep != "ROOT" or adp.index > verb.index:
        return False
    return not any(c.dep == "cp" for c in sentence.children(verb))


def _objects(
    sentence: ParsedSentence, verb: TokenView, children: list[TokenView]
) -> list[TokenView]:
    objects = [c for c in children if c.dep == "oa" and _is_noun(c)]
    return objects or _passive_subjects(sentence, verb)


def _passive_subjects(sentence: ParsedSentence, verb: TokenView) -> list[TokenView]:
    """The subject of a werden passive: *Die Entscheidung muss getroffen werden.*"""
    if verb.tag != "VVPP" or verb.dep != "oc":
        return []
    node = sentence.head_of(verb)
    if node is None or node.lemma != "werden":
        return []
    while True:
        subjects = [c for c in sentence.children(node) if c.dep == "sb" and _is_noun(c)]
        parent = sentence.head_of(node)
        if subjects or node.dep != "oc" or parent is None or parent.pos != "AUX":
            return subjects
        node = parent


def _is_noun(token: TokenView) -> bool:
    # The model tags the noun Acht (in Acht nehmen) as a proper noun or a numeral. Trust the
    # STTS tag NN, and a capitalised numeral, since real numerals are lowercase.
    if token.pos == "NOUN" or token.tag == _COMMON_NOUN:
        return True
    return token.pos == "NUM" and token.text[:1].isupper()


def _is_expletive(token: TokenView) -> bool:
    return token.dep in _SUBJECT_DEPS and token.text.lower() == "es"


def _has_determiner(sentence: ParsedSentence, noun: TokenView, but: str | None = None) -> bool:
    """Whether the noun has a determiner or numeral, ignoring one with the lemma `but`."""
    return any(c.pos in _DETERMINER_POS and c.lemma != but for c in sentence.children(noun))


def _first(tokens: list[TokenView], predicate: Callable[[TokenView], bool]) -> TokenView | None:
    return next((t for t in tokens if predicate(t)), None)

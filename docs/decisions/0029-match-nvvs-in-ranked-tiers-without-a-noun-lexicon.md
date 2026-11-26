---
title: Match NVVs in ranked tiers on the dependency parse, without a noun lexicon
summary: A light verb's NVV is the first non-empty tier of cvc phrase or variant, bare object, last bare PP, other object; no list of NVV nouns is used.
status: active
updated: 2026-11-26
---

# Match NVVs in ranked tiers on the dependency parse, without a noun lexicon

## Context

R8 and [0016](0016-use-standard-python-tooling.md) fix the approach (spaCy dependency parse plus a light-verb list) but not the rules. A light verb often has more than one candidate for the nominal part: *den Mitarbeitern Laptops zur Verfügung stellen* has an object and a prepositional phrase, *großen Wert auf Qualität legen* has both too, but here the object is the NVV. spaCy has no notion of abstract nouns, and R13 rules out a curated NVV list. Trying `de_core_news_lg` on sample sentences showed:

- The TIGER label `cvc` (collocational verb construction) marks most PP chunks (*zur Verfügung*, *in Kraft*, *ums Leben*, *unter Druck*), but also some complements of an object (*Anspruch auf Vollständigkeit*), and misses some chunks (*in Betracht*, *in Acht*, labelled `mo`).
- Fronted phrases (*Nach langer Diskussion traf der Rat eine Entscheidung*) and phrases of place (*im Garten*) look like bare PPs.

## Decision

Match on the parse alone, in tiers. For each verb whose infinitive with its own separable prefix is on the light-verb list, keep only the first non-empty tier:

1. one-word spelling variants (*infrage*) and PPs labelled `cvc`;
2. accusative object nouns without a determiner, where *kein* does not count;
3. the last bare PP: uncontracted preposition, singular noun, no determiner or numeral, not before the finite verb of a main clause;
4. any other accusative object noun, or the subject of a *werden* passive.

Next to an object, a PP whose preposition usually introduces the object's complement (*an, auf, bei, für, gegen, mit, nach, über, von*) never counts, even with `cvc`. *es gibt* and *es geht um* are skipped. The rules are in `adapters/nlp/match.py` and [NVV extraction](../system-design/nvv-extraction.md).

## Alternatives considered

- **Every object and PP of a light verb:** simplest, but each NVV with an object gives a second, wrong chunk (*laptop|stellen*), which costs an LLM call and a junk card.
- **A list of NVV nouns, or of abstract-noun suffixes, to filter objects:** cuts false positives such as *vase|stellen*, but *Rolle*, *Frage* and *Mühe* have no telltale suffix, so it becomes a curated list, which R13 excludes, and it would hide new chunks.
- **Trust `cvc` alone for PPs:** misses *in Betracht ziehen* and *sich in Acht nehmen*, a 0011 row.

## Consequences

- The golden corpus baseline ([0031](0031-guard-extraction-with-a-golden-corpus-baseline.md)) is 0.889 precision and 0.923 recall. Most false positives are concrete objects (*das Buch nehmen*); ranking by occurrence (R13) pushes them down, because they rarely repeat across sources.
- The rules depend on the TIGER labels of the German spaCy models. A model upgrade must rerun the `nlp` tests.
- A noun or suffix filter can still be added later as an extra tier rule, measured against the same corpus.

## Related

- [0011 Normalise NVV chunk keys](0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)
- [0030 Keep a verb's own separable prefix in the key](0030-keep-a-verbs-own-separable-prefix-in-the-key.md)
- [DeepSeek chat advice](../research/deepseek-chat-advice.md)

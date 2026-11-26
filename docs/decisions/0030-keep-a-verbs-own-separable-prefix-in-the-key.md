---
title: Keep a verb's own separable prefix in the key, and list light verbs by full infinitive
summary: The verb in a chunk key includes its own separated prefix (nahm Kontakt auf → kontakt|aufnehmen); the light-verb list holds full infinitives such as aufnehmen.
status: active
updated: 2026-11-26
---

# Keep a verb's own separable prefix in the key, and list light verbs by full infinitive

## Context

[0011](0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md) says the key's verb is the infinitive "without any separable prefix that belongs to a different verb", but does not say what happens to the verb's own prefix. In a main clause German separates it: *Die Polizei nahm Kontakt mit der Familie auf*. spaCy lemmatises *nahm* as *nehmen* and attaches *auf* as a separate token with the label `svp`; in the perfect, *aufgenommen* is lemmatised as *aufnehmen*. Without a rule, one chunk gets two keys depending on the tense. The light-verb list has the same question: is *aufnehmen* on it because *nehmen* is?

## Decision

- The key's verb is the verb lemma with the verb's own separated prefix (the `svp` dependent of that verb) in front: *nahm … auf* and *aufgenommen* both give `aufnehmen`, so *Kontakt aufnehmen* is `kontakt|aufnehmen`.
- A prefix attached to another verb in the sentence is never used, which is what 0011 rules out.
- The light-verb list holds full infinitives. A prefixed verb is a light verb only if it is listed itself (`aufnehmen`, `ausüben`). *Die Polizei nahm den Mann fest* is not matched, because `festnehmen` is not on the list.
- A one-word spelling variant labelled `svp` (*kam zustande*) is mapped through the variant table, not read as a prefix.

## Alternatives considered

- **Drop every separable prefix and match the base verb:** *nahm … fest* would become `mann|nehmen`, and *Kontakt aufnehmen* would collide with *Kontakt nehmen*.
- **Keep the prefix in the key but match the list on the base verb:** every prefixed verb of a light verb (*feststellen*, *einstellen*, *vorstellen*) would count as a light verb, with many false positives.

## Consequences

- No change to the key format, so no migration: it only settles a case 0011 left open.
- Adding a prefixed light verb means adding its full infinitive to `light_verbs.txt`.

## Related

- [0011 Normalise NVV chunk keys](0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)
- [0029 Match NVVs in ranked tiers](0029-match-nvvs-in-ranked-tiers-without-a-noun-lexicon.md)
- [NVV extraction](../system-design/nvv-extraction.md)

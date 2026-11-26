---
title: NVV extraction
summary: How the NVV extractor parses with spaCy, matches light verbs in ranked tiers, builds 0011 keys and context, and how its quality is guarded.
status: active
updated: 2026-11-26
---

# NVV extraction

## Purpose

Explains how German text becomes Nomen-Verb-Verbindung candidates (R8, R10): which module does what, the matching rules, how keys are built, and how to change the word lists without making extraction worse. Read this before touching `adapters/nlp/`, the light-verb list or the golden corpus.

## Modules

Everything lives in `src/learn_german/adapters/nlp/`. Only `parse.py` imports spaCy, so the rules are unit-tested on hand-built tokens without the 500 MB model.

| Module | Role |
|---|---|
| `tokens.py` | `TokenView` (index, text, lemma, POS, STTS tag, TIGER dependency, head, morphology) and `ParsedSentence`. No spaCy. |
| `parse.py` | `SpacyParser`: loads `de_core_news_lg` once, on first use; splits text into paragraphs at blank lines, collapses whitespace, batches paragraphs through `nlp.pipe`, and converts every sentence into `TokenView`s. A missing model raises `NlpModelMissingError` ([0027](../decisions/0027-settle-shared-dependencies-before-parallel-tracks.md)). |
| `match.py` | `find_matches`: finds each light verb and the nominal part of its NVV ([0029](../decisions/0029-match-nvvs-in-ranked-tiers-without-a-noun-lexicon.md)). |
| `keys.py` | `build_key`: turns a match into a `ChunkKey` ([0011](../decisions/0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md), [0030](../decisions/0030-keep-a-verbs-own-separable-prefix-in-the-key.md)). |
| `lexicon.py` | Reads `data/light_verbs.txt` and `data/spelling_variants.tsv` through `importlib.resources`. |
| `extractor.py` | `NvvExtractor`, the `ChunkExtractor` port: parse, match, key, deduplicate per sentence, add the context window. |

`bootstrap.extractor_registry()` maps the name `nvv` to `NvvExtractor.default()`. Building it is cheap; the model loads on the first `extract`.

## Matching

A verb counts as a light verb when its infinitive, with its own separable prefix, is on the light-verb list: *nahm … auf* is `aufnehmen`, *stellte … fest* is `feststellen` and so is not a light verb. Each dependent that could be the NVV's nominal part goes into a tier; only the first non-empty tier is kept:

| Tier | Candidate | Example |
|---|---|---|
| 1 | One-word spelling variant, or a PP labelled `cvc` (collocational verb construction) | *stellt … infrage*, *stellte … zur Verfügung* |
| 2 | Accusative object without determiner; *kein* does not count as one | *Rücksicht nehmen*, *keinen Anspruch erheben* |
| 3 | The last bare PP: uncontracted preposition, singular noun, no determiner or numeral, not fronted before a finite main verb | *in Betracht ziehen*, *auf Kritik stoßen* |
| 4 | Any other accusative object, or the subject of a *werden* passive | *traf eine Entscheidung*, *Die Entscheidung wurde getroffen* |

Further rules:

- If the verb has an object, a PP with *an, auf, bei, für, gegen, mit, nach, über* or *von* is the object's complement (*Wert legen auf*), never the NVV, even when the model labels it `cvc`.
- *es gibt* and *es geht um* are skipped.
- A reflexive pronoun (STTS `PRF`) attached to the verb as accusative or dative makes the key reflexive.
- A token is a noun if its POS is `NOUN` or its STTS tag is `NN`, or if it is a capitalised numeral: the model tags *Acht* in *in Acht nehmen* as a numeral or proper noun.

## Keys and candidates

`build_key` lowercases lemmas, expands contractions (*zur* → `zu`), adds `sich` for a reflexive, puts the verb's own separable prefix in front of the verb lemma, and maps one-word spellings through the variant table (*infrage* → `frage|in`). A lemma that `ChunkKey` rejects (digits, accents) drops the match.

Each candidate holds the sentence and a context window: the sentence plus one sentence on each side, joined by single spaces. A key found twice in one sentence gives one candidate.

## Data files

Both files are lowercase, sorted (ä, ö, ü as a, o, u; ß as ss), without duplicates; unit tests enforce this.

- `light_verbs.txt`: one infinitive per line, with a separable prefix where the verb has one. Every verb added can add false positives.
- `spelling_variants.tsv`: one-word form, noun lemma, preposition, tab-separated.

After changing either file, run `make test-nlp`. If precision or recall drops below the baseline, the change makes extraction worse.

## Quality guard

| Test | Where | Needs model |
|---|---|---|
| Matcher and key builder on hand-built parses, every 0011 row, data-file format | `tests/unit/nlp/` | no |
| Every 0011 row with a separated verb, perfect tense, subordinate clause, negation and passive | `tests/nlp/test_key_table.py` | yes |
| Golden corpus: precision and recall at or above the baseline | `tests/nlp/test_golden_corpus.py`, `tests/data/nlp/` | yes |

The golden corpus ([0031](../decisions/0031-guard-extraction-with-a-golden-corpus-baseline.md)) has 70 hand-written sentences, 20 of them without an NVV. Baseline with `de_core_news_lg` 3.8.0, recorded 2026-11-26:

| Precision | Recall | True positives | False positives | False negatives |
|---|---|---|---|---|
| 0.889 (stored rounded down, 0.888) | 0.923 | 48 | 6 | 4 |

Run the `nlp` tests with `make test-nlp` (installs the model extra). pytest-socket warns once that a test tried to open a socket: that is urllib3 probing for IPv6 when spaCy imports it. No connection is made.

## Known limitations

- Concrete objects of a light verb are taken as NVVs: *stellte die Vase auf den Tisch* gives `vase|stellen`. There is no noun lexicon (R13 rules out a curated list; [0029](../decisions/0029-match-nvvs-in-ranked-tiers-without-a-noun-lexicon.md)).
- A bare PP of place can pass: *nach Hause kommen* gives `haus|nach|kommen`.
- PP chunks with an article (*auf den Markt bringen*, *auf die Nerven gehen*) and *im Mittelpunkt stehen* are missed unless the model labels them `cvc`.
- spaCy lemma errors give wrong or no keys: *leisteten* is lemmatised as *leisteen*, so *Hilfe leisteten* is missed.
- *Es stellt sich die Frage* (noun as subject of a reflexive) is not matched.

## Related

- [Pipeline](pipeline.md)
- [Code architecture](code-architecture.md)
- [0011 Normalise NVV chunk keys](../decisions/0011-normalise-nvv-chunk-keys-as-noun-prep-verb.md)
- [Testing strategy](../development/testing-strategy.md)

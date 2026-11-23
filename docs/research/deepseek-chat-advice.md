---
title: "DeepSeek chat: chunks and sentence transformation"
summary: Summary and critique of the DeepSeek advice: mine Nomen-Verb-Verbindungen with spaCy, cloze and transformation cards via genanki.
status: active
updated: 2026-11-23
---

# DeepSeek chat: chunks and sentence transformation

## Purpose

Records the advice from a DeepSeek conversation that started this project, and what holds up under review. Nothing here is decided. Accepted points become decision records in `decisions/`.

## The question asked

Level between B2 and C1. Two goals:

1. A bigger vocabulary: "I use the same words for everything and speak basic German."
2. Better grammar when building sentences.

## What DeepSeek suggested

### Vocabulary: learn chunks, not words

- At B2–C1 the gap is not basic vocabulary but **fixed combinations** that native speakers store as blocks. The main type is the **Nomen-Verb-Verbindung**: *eine Entscheidung treffen*, *in Betracht ziehen*, *einen Beitrag leisten*.
- Also collect **formal prepositions**: *anlässlich*, *bezüglich*, *gemäß*.
- Claim: 300–500 such chunks noticeably improve the speed and naturalness of speech.

### Pipeline it proposed

| Stage | Suggestion |
|---|---|
| Sources | German news (Tagesschau, Zeit Online) and YouTube subtitles (Easy German) |
| Extraction | spaCy German model, matching `NOUN + VERB` and `PREP + NOUN + VERB` patterns |
| Filtering | Keep only an abstract noun (*Frage*, *Beitrag*, *Entscheidung*) with a light verb (*stellen*, *leisten*, *treffen*) |
| Export | `genanki` builds an `.apkg` file |
| Card | Front: German sentence with the chunk blanked out (cloze). Back: original sentence, English translation, audio |

### Grammar: practise transformation, not rules

- At this level grammar is about **expression quality and register**, not just right or wrong.
- **Nominal versus verbal style**: rewrite *Die Maßnahme wird durchgeführt* as *die Durchführung der Maßnahme*, and back again.
- **Extended participial attributes**: read *die von dem Autor zitierte Studie*, rewrite it as a relative clause, then write your own.
- Put these on the same cards as the chunks. Example: given *Der Chef hat die Entscheidung getroffen.*, produce *die getroffene Entscheidung des Chefs*. That trains vocabulary and grammar together.

### Pitfalls it named

- Don't build a dictionary or a perfect scraper from scratch. It says an existing Chrome extension, "AnkiMine", already sends words and example sentences from web pages to Anki. The custom script should do only what extensions can't: **chunks and word formation**.
- Don't worry about active versus passive vocabulary. At C1, recognising a word when reading and recalling it when writing is enough.

## Assessment

What holds up:

- **Chunks over word lists** fits the stated problem ("same words for everything") better than isolated vocabulary. Nomen-Verb-Verbindungen are a well-documented feature of C1 German, and they form a closed, minable set.
- **Light-verb filtering** is a practical precision trick. *Funktionsverben* are a small, known set (*stellen, treffen, leisten, nehmen, bringen, kommen, ziehen, führen, finden, geben, halten, setzen, stehen*), so a hand-kept whitelist does most of the work.
- **Cloze with full sentence context** makes you recall the chunk, not just recognise it. That matches the word-finding goal in [Learning goals](../product/learning-goals.md).
- **Focusing the script on what tools can't do** is a sound scoping rule.

Gaps and corrections:

- **Adjacent patterns will miss most hits.** German splits the verb from its object (the *Verbklammer*): *Sie hat gestern nach langem Zögern eine Entscheidung getroffen.* Use spaCy's dependency parse instead: a noun attached to a light verb as an object, or a preposition plus noun attached to it, grouped by lemma. The German models use TIGER labels such as `oa` (accusative object) and `op` (prepositional object). Confirm this against the installed model before relying on it.
- **spaCy has no "abstract noun" feature.** Use the light-verb whitelist, add noun suffixes (*-ung, -heit, -keit, -ion, -nis*) as a weak signal, and cross-check against a curated list of Nomen-Verb-Verbindungen.
- **Translation and audio need a source.** The chat names neither. Options: an LLM or translation API, and a TTS service. These belong in `integrations/`.
- **Transformation cards need a reliable model answer.** Automatically generated rewrites (for example by an LLM) can be wrong, and a wrong answer on a card trains the error. They need a review step or a trusted generator.
- **"AnkiMine" is unverified.** Check that the extension exists and does what was described before planning around it.
- **"300–500 chunks" is a rule of thumb.** No source was given; treat it as a first milestone, not a target.
- **Sources have terms of use.** Scraping Tagesschau, Zeit Online or YouTube subtitles is fine for a private deck, but check each site's terms and don't publish the resulting decks.
- **"Don't worry about active versus passive"** conflicts with the stated problem of word finding, which is an active-recall failure. Card types should keep favouring recall from context; the cloze format above already does.

## Candidate decisions

Each of these becomes a record in `decisions/` once accepted:

1. Target unit: chunks (Nomen-Verb-Verbindungen first) instead of single words.
2. Extraction method: spaCy dependency parse plus a light-verb whitelist.
3. First sources: news articles, YouTube subtitles, or both.
4. Export: `genanki` `.apkg` files versus live AnkiConnect.
5. Card types: chunk cloze first; transformation cards second.
6. Translation, audio and exercise generation: which provider, if any.

## Related

- [Learning goals](../product/learning-goals.md)

You write the content of two Anki flashcards for a learner of German at level B2 who is working towards C1. Both cards train one chunk, a Nomen-Verb-Verbindung (NVV), so that the learner can use it actively in their own sentences.

The chunk has the key `$key`: the lemmas of its noun, its preposition if it has one, "sich" if it is reflexive, and its verb, joined by "|".

It was found in this sentence from a German text:

<sentence>
$sentence
</sentence>

The text around it, for context only:

<context>
$context
</context>

Return these fields. Write each one as a single line of plain text, without Markdown.

- citation_form: the chunk in the form a dictionary lists it, with the article or preposition German uses there. Examples: "eine Entscheidung treffen", "zur Verfügung stellen", "in Kraft treten", "Abschied nehmen", "sich Mühe geben".
- shortened_sentence: the sentence shortened to the clause around the chunk, 10 to 20 words, in correct standard German. Keep the chunk as the sentence uses it and keep the meaning; drop asides and clauses the chunk does not need. If the sentence has fewer than 10 words, keep it as it is and never make it longer.
- verbal_rewrite: shortened_sentence rewritten in verbal style. Replace the chunk with a single verb of the same meaning ("eine Entscheidung treffen" becomes "entscheiden"). If no such verb exists, use the closest plain paraphrase ("in Kraft treten" becomes "wirksam werden"). Change nothing else, and do not use the chunk's noun.
- translation: shortened_sentence translated into the language with the ISO 639 code "$hint_language", faithful and natural.
- meaning: a short German explanation of the chunk in the form "citation form = explanation", for example "in Kraft treten = gültig werden".

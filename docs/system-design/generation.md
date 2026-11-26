---
title: Generation
summary: How a CardRequest becomes checked, cached CardContent: provider port, versioned prompt, sanity checks, cache decorator and wiring.
status: active
updated: 2026-11-26
---

# Generation

## Purpose

Explains the generate stage of `sync` ([Pipeline](pipeline.md)): one LLM call per chunk turns a `CardRequest` into the `CardContent` that fills both notes ([0012](../decisions/0012-make-both-cards-practise-the-chunk.md)). Read this before changing the prompt, adding a provider or touching the cache. The Claude API specifics are in [Claude API](../integrations/claude-api.md).

## Modules

| Module | Role |
|---|---|
| `ports.LLMProvider` | `name`, `model`, `prompt_version` and `generate(request) -> CardContent`. |
| `adapters/llm/prompt.py` | `PROMPT_VERSION`, `load_template()` and the pure `render_prompt(template, request)` ([0035](../decisions/0035-version-the-card-prompt-as-a-template-with-a-pinned-hash.md)). |
| `adapters/llm/prompts/card_v1.md` | The prompt template of `card-v1`. |
| `adapters/llm/schema.py` | `CardOutput`, the pydantic model of the answer, and `CARD_SCHEMA`, the JSON schema sent as output format. |
| `adapters/llm/claude.py` | `AnthropicProvider` ([0037](../decisions/0037-call-claude-with-a-json-schema-and-split-errors-into-fatal-and-item.md)). |
| `adapters/llm/errors.py` | `LLMAccessError` (fatal) and `LLMRequestError` (item). |
| `application/generation/checks.py` | Sanity checks and the `CheckedProvider` decorator ([0036](../decisions/0036-check-card-content-then-cache-it-in-its-own-transaction.md)). |
| `application/generation/caching.py` | `cache_key` and the `CachingProvider` decorator. |
| `tests/fakes/llm.py` | `FakeProvider`: deterministic content, per-key failures and scripted content. |

## Wiring

```
CachingProvider(CheckedProvider(AnthropicProvider.create(api_key, model=settings.model)), uow, clock)
```

The order matters: the checks run before the cache, so only content that passed is stored. Any other provider goes in place of `AnthropicProvider` and gets both decorators unchanged. Bootstrap does this wiring in M7.

`CachingProvider.generate` opens its own unit-of-work blocks, so `sync` calls it before opening the chunk's `with uow:` block, not inside it.

## The request

`CardRequest` carries the chunk key and kind, the sentence and context picked by `ShortestSentencePicker` ([0032](../decisions/0032-feed-cards-from-the-shortest-sentence-of-ten-words.md)), and the hint language. The prompt asks for:

| Field | Note field | Rule in the prompt |
|---|---|---|
| `citation_form` | `Chunk` | Dictionary form with the usual article or preposition ([0028](../decisions/0028-let-the-llm-supply-the-citation-form.md)) |
| `shortened_sentence` | `Answer` | The clause around the chunk, 10 to 20 words; a sentence under 10 words is kept and never made longer |
| `verbal_rewrite` | transformation `Prompt` | The chunk replaced by one verb, or the closest plain paraphrase |
| `translation` | translation `Prompt` | `shortened_sentence` in the hint language |
| `meaning` | `Meaning` | One German line, "citation form = explanation" |

## Sanity checks

`check_card` raises a `GenerationError` listing every failed check, so the chunk stays pending ([0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md)):

| Check | Passes when |
|---|---|
| Noun in the answer | `shortened_sentence` contains the key's noun, ignoring case and umlauts (*Anträge* matches *antrag*) |
| Length | `shortened_sentence` has 8 to 25 words; if the source has fewer than 10, at most as many words as the source |
| Citation form | `citation_form` contains the key's noun and verb |
| Meaning | `meaning` is one line |

Words are counted like the picker counts them: whitespace-separated tokens with a letter or digit.

## The cache

The key is the SHA-256 of canonical JSON holding provider, model, prompt version and the whole request. The `llm_cache` row stores the content as JSON with provider, model, prompt version and creation time ([Data model](../data/data-model.md)). A hit makes no provider call. A change of any key component is a miss, so a new prompt version, a new model or a newly picked sentence pays once more. An entry that no longer decodes is a miss and is replaced.

## Changing the prompt

1. Add `prompts/card_vN.md` and map it in `_TEMPLATE_FILES`; set `PROMPT_VERSION = "card-vN"`.
2. Record the template's SHA-256 in `tests/data/llm/prompt_hashes.json` and update the golden file `tests/data/llm/card_v1_prompt.golden.txt` (or add one for the new version).
3. Run `tools/eval/run_eval.py` and read the cards ([Claude API](../integrations/claude-api.md#manual-evaluation)).

The hash test fails if step 1 is skipped.

## Related

- [Pipeline](pipeline.md)
- [Note types](../learning-design/note-types.md)
- [Code architecture](code-architecture.md)

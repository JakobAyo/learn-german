---
title: Claude API
summary: How AnthropicProvider calls the Claude API: settings, request, retries, how each failure is reported, cost, mocked tests and the eval script.
status: active
updated: 2026-11-26
---

# Claude API

## Purpose

Describes the one external call of card generation: what is sent to the Claude API, what comes back, and what happens when it fails. Read this before changing `adapters/llm/`, the model setting or the prompt. The choices are recorded in [0037](../decisions/0037-call-claude-with-a-json-schema-and-split-errors-into-fatal-and-item.md); how the provider fits into `sync` is in [Generation](../system-design/generation.md).

## Settings

| Setting | Default | Where |
|---|---|---|
| API key | none | `ANTHROPIC_API_KEY` in the environment or `.env` ([Configuration](../development/configuration.md)) |
| Model | `claude-opus-5-5` ([0015](../decisions/0015-set-v1-run-defaults.md)) | `model` setting, `LEARN_GERMAN_MODEL` |
| Hint language | none, required | `hint_language` setting; goes into the prompt as an ISO 639 code |

Effort (`medium`), `max_tokens` (16 000) and retries (2) are constructor defaults of `AnthropicProvider`, not user settings.

## Request

One `POST /v1/messages` per chunk, through the Anthropic SDK (`anthropic` 2.x, on `httpx2`):

- `model`: the model setting.
- `messages`: one user message, the rendered card prompt ([0035](../decisions/0035-version-the-card-prompt-as-a-template-with-a-pinned-hash.md)).
- `output_config.format`: a JSON schema with the five required string fields of `CardContent` and no others.
- `output_config.effort`: `medium`. `thinking` is not sent; Claude Opus 5.5 thinks adaptively.

The SDK sends the key as `Authorization: Bearer …`.

## Response

The text blocks of the answer are joined and validated by the pydantic model `CardOutput` (`adapters/llm/schema.py`): every field present, a string, non-empty after stripping, no extra fields. Thinking blocks are ignored. The result becomes a `CardContent`, which then passes the sanity checks of [Generation](../system-design/generation.md#sanity-checks).

## Failures

| What happens | Error | Effect on `sync` |
|---|---|---|
| Key rejected (401), no permission (403), unknown model (404), bad request (400), no credit (402) or a spend limit (429 with a spend-limit code) | `LLMAccessError`, a `FatalError` | Run stops; the message says what to fix |
| Rate limit, server error, overload, timeout or connection error, still failing after the SDK's retries | `LLMRequestError`, an `ItemError` | Chunk stays pending with the error; run continues |
| Refusal, answer cut off at `max_tokens`, empty text, invalid JSON, schema violation | `GenerationError`, an `ItemError` | Same |
| Empty API key | `MissingCredentialsError`, a `FatalError` | Run stops before any call |

The SDK retries connection errors, 408, 409, 429 and 5xx twice with backoff, honouring `retry-after`. A refusal is not retried on another model, so tags and cache keys always name the model that wrote the card.

## Cost

Claude Opus 5.5 costs $4 per million input tokens and $20 per million output tokens, thinking included. The prompt is under a thousand input tokens; the answer is a few hundred tokens plus thinking at medium effort. Each answer that passes the checks is cached, so it is paid for once ([0036](../decisions/0036-check-card-content-then-cache-it-in-its-own-transaction.md)); an answer that fails is paid for again on the next run. Debug logging records each call's request ID and token counts.

## Testing

Tests never touch the network. `tests/integration/llm/mock_api.py` scripts replies behind `httpx2.MockTransport` and passes the mocked `httpx2.Client` to `AnthropicProvider.create(..., http_client=...)`. Error replies carry `retry-after-ms: 1`, so the SDK's real retry loop runs without sleeping.

## Manual evaluation

`tools/eval/run_eval.py` runs the prompt on the hand-written chunks in `tools/eval/chunks.tsv` against the real API and prints each chunk's content and sanity-check problems as one JSON line. It needs `ANTHROPIC_API_KEY` and a hint language, costs a few cents per chunk, bypasses the cache, and refuses to run when `CI` is set:

```bash
uv run python tools/eval/run_eval.py --hint-language en [--model claude-opus-5-5] [--effort high]
```

Run it after a prompt or model change and read the cards before bumping `PROMPT_VERSION` for real use.

## Related

- [Generation](../system-design/generation.md)
- [Note types](../learning-design/note-types.md)
- [0004 Pluggable LLM provider](../decisions/0004-generate-card-content-through-a-pluggable-llm-provider.md)

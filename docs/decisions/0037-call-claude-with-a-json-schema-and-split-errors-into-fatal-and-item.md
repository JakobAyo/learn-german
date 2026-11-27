---
title: Call Claude with a JSON-schema output format and split API errors into fatal and item
summary: One Messages call with a JSON-schema output at medium effort, no refusal fallback; rejected access is fatal, failures after retries are item errors.
status: active
updated: 2026-11-26
---

# Call Claude with a JSON-schema output format and split API errors into fatal and item

## Context

[0004](0004-generate-card-content-through-a-pluggable-llm-provider.md) makes the Claude API the first provider and [0015](0015-set-v1-run-defaults.md) sets `claude-opus-5-5` as default model. The [Roadmap](../product/roadmap.md) asks for structured JSON output against the `CardContent` schema, SDK retries, authentication failures as `FatalError` and invalid output as `ItemError`. The SDK raises many error classes, and [0014](0014-keep-progress-when-a-run-fails-partway.md) needs each sorted into "stop the run" or "record and continue". The SDK 2.x runs on `httpx2` and accepts a custom `httpx2.Client`, which is how tests mock it ([0027](0027-settle-shared-dependencies-before-parallel-tracks.md)).

## Decision

- **One `messages.create` call per chunk** with the rendered prompt as the only user message and `output_config.format` set to a JSON schema. The schema is built from the pydantic model `CardOutput`: five required string properties, `additionalProperties: false`, nothing else, so only keywords structured outputs accepts are sent.
- **Validation is ours:** the answer's text blocks are joined and validated with `CardOutput.model_validate_json`, which strips whitespace and rejects empty, missing or extra fields. Malformed JSON and schema violations become `GenerationError`. `messages.parse` is not used, so every failure gets the same error type and message.
- **Request settings:** `max_tokens` 16 000 without streaming. `thinking` is not sent, so Claude Opus 5.5 thinks adaptively, which it cannot switch off. `effort` is set to `medium` explicitly, the model's default; it is a constructor argument for `tools/eval`, not a user setting.
- **Retries** are the SDK's (`max_retries`, default 2): connection errors, 408, 409, 429 and 5xx, honouring `retry-after`.
- **No refusal fallback.** A `refusal` stop reason, a `max_tokens` cut-off or an answer without text is a `GenerationError`. The SDK's server-side fallback would let another model write the card while the note is tagged ([0005](0005-push-cards-automatically-with-tagging-and-dry-run.md)) and cached under the configured one.
- **Error mapping:**

  | SDK error | Raised as | Why |
  |---|---|---|
  | `BadRequestError` (400), `AuthenticationError` (401), `PaymentRequiredError` (402), `PermissionDeniedError` (403), `NotFoundError` (404), spend-limit 429s | `LLMAccessError` (`FatalError`) | Bad key, unknown model, wrong request shape or no credit: every further call fails too |
  | Other `APIError`: rate limit, 5xx, overload, timeouts, connection errors, after retries | `LLMRequestError` (`ItemError`) | Transient; the chunk stays pending and the next run retries it |
  | Empty API key | `MissingCredentialsError` (`FatalError`) | Checked before the client is built |

- **Construction:** `AnthropicProvider.create(api_key, model=…, http_client=None)` builds the SDK client; tests pass an `httpx2.Client` over `httpx2.MockTransport`. Error responses in tests carry `retry-after-ms: 1`, so retries do not sleep.

## Alternatives considered

- **`messages.parse` with the pydantic model:** less code, but its own exceptions for unparsable output would need a second mapping, and `min_length` would end up in the schema sent to the API.
- **A strict tool instead of an output format:** Claude Opus 5.5 does not allow forcing a tool, so the model could answer without calling it.
- **High effort:** better on hard rewrites, at roughly twice the thinking tokens. Medium matches the cost estimate in 0015; `tools/eval` can compare levels on real chunks before this changes.
- **Server-side refusal fallback:** see above. A refusal on hand-picked German news sentences is rare; the chunk stays pending and is visible in the run summary.
- **Connection errors as fatal:** would stop a run after one dropped connection; after retries each chunk fails quickly enough when the network is down.

## Consequences

- A wrong model ID or a missing credit stops `sync` before more chunks are tried, with a message that says what to fix.
- An answer that fails validation is paid for and not cached; the next run pays again ([0036](0036-check-card-content-then-cache-it-in-its-own-transaction.md)).
- Switching to a model without structured outputs or effort support gives a 400, which stops the run with a message pointing at the model setting.

## Related

- [Claude API](../integrations/claude-api.md)
- [Generation](../system-design/generation.md)

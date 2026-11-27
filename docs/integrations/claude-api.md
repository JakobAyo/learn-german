---
title: Claude API
summary: How AnthropicProvider calls the Claude API: setup, key, model, request, failures and their messages, cost, caching, logging, tests and the eval script.
status: active
updated: 2026-11-27
---

# Claude API

## Purpose

Describes the one external call of card generation: what is sent to the Claude API, what comes back, and what happens when it fails. Read this before changing `adapters/llm/`, the model setting or the prompt. The choices are recorded in [0037](../decisions/0037-call-claude-with-a-json-schema-and-split-errors-into-fatal-and-item.md); how the provider fits into `sync` is in [Generation](../system-design/generation.md).

## Setup

1. Create an API key in the [Claude Console](https://platform.claude.com/) (Settings, API keys). The account needs credit or a payment method.
2. Give it to the tool as `ANTHROPIC_API_KEY`: exported in the shell, or in a `.env` file in the directory `learn-german` is run from. Never in `config.toml`, which is meant to be shareable, and never in the repository ([0002](../decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md)).
3. Check it with `learn-german sync --dry-run --cap 1`: without a key it stops at once with a message saying so, before it opens the database or asks Anki ([0046](../decisions/0046-check-settings-and-anki-before-selecting-and-keep-dry-runs-read-only.md)).

`add`, `status` and `reextract` do not need it.

## Settings

| Setting | Default | Where |
|---|---|---|
| API key | none | `ANTHROPIC_API_KEY` in the environment or `.env` ([Configuration](../development/configuration.md)) |
| Model | `claude-opus-5-5` ([0015](../decisions/0015-set-v1-run-defaults.md)) | `model` setting, `LEARN_GERMAN_MODEL` |

Effort (`medium`), `max_tokens` (16 000) and retries (2) are constructor defaults of `AnthropicProvider`, not user settings.

### The API key

`Settings.anthropic_api_key` is a `SecretStr`, so it does not show in a repr. `bootstrap` reads it with `require_anthropic_api_key()` and passes it only to `anthropic.Anthropic(api_key=…)`. The tool never prints or logs it: `--verbose` leaves the SDK's and httpx2's loggers at WARNING, and a filter masks anything that looks like `sk-ant-…` in log lines ([0048](../decisions/0048-log-with-stdlib-logging-behind-a-global-verbose-flag.md)). A test runs `-v sync` with a known key and checks that it appears nowhere in the output.

### Choosing the model

The default is Claude Opus 5.5 ([0015](../decisions/0015-set-v1-run-defaults.md)). Another model must support structured outputs (`output_config.format`) and `output_config.effort`; otherwise the API answers 400 and the run stops with a message naming the model. Run `tools/eval/run_eval.py --model <id>` before switching. The model is part of every cache key and of the `model::` tag, so a switch regenerates nothing already cached under the old model and tags new notes with the new one.

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

| What happens | Error | Effect on `sync` | Next step the message gives |
|---|---|---|---|
| Key rejected (401) | `LLMAccessError`, a `FatalError` | Run stops, exit 2; notes already added stay | Check `ANTHROPIC_API_KEY` |
| Unknown model (404) | `LLMAccessError` | Same | Set a valid model ID in `model` or `LEARN_GERMAN_MODEL` |
| Bad request (400) | `LLMAccessError` | Same | Check that the model supports structured outputs and effort, and the account is active |
| No permission (403), no credit (402), a spend limit (429 with a spend-limit code) | `LLMAccessError` | Same | Check credit, spend limits and the key's permissions in the Claude Console |
| Rate limit, server error, overload, timeout or connection error, still failing after the SDK's retries | `LLMRequestError`, an `ItemError` | Chunk stays pending with the error; run continues, exit 1 | Run `sync` again later |
| Refusal | `GenerationError`, an `ItemError` | Same | None needed; the next sync asks again, and a chunk Claude keeps declining just keeps failing |
| Answer cut off at `max_tokens`, empty text, invalid JSON, schema violation, failed sanity check | `GenerationError` | Same | None needed; the next sync asks again |
| No or empty API key | `MissingCredentialsError`, a `FatalError` | Run stops before the database, Anki or any call, exit 2 | Create a key in the Claude Console and set `ANTHROPIC_API_KEY` |

The SDK retries connection errors, 408, 409, 429 and 5xx twice with backoff, honouring `retry-after`. A refusal is not retried on another model, so tags and cache keys always name the model that wrote the card.

## Cost

Claude Opus 5.5 costs $4 per million input tokens and $20 per million output tokens, thinking included. The prompt is under a thousand input tokens; the answer is a few hundred tokens plus thinking at medium effort, so a chunk costs a few cents. A `sync` at the default cap of 10 chunks costs well under a dollar. `learn-german -v sync` logs each call's request ID and token counts, which is the way to measure the real figure; the Claude Console's usage page shows the total.

What is paid for:

- One call per chunk that has no cached answer. The chunk's one note comes from that answer.
- `sync --dry-run` pays for its calls too, but caches the answers, so the real `sync` after it pays nothing for them.
- An answer that fails a check, is refused or cut off is not cached and is paid for again on the next run.
- The SDK's retries after a rate limit or server error are not billed, since those requests produced no answer.

## Caching

**Local answer cache.** `CachingProvider` stores every answer that passed the checks in the `llm_cache` table, keyed by a hash of provider, model, prompt version and the request (chunk key, chunk kind, sentence, context) ([0036](../decisions/0036-check-card-content-then-cache-it-in-its-own-transaction.md)). The same request is never paid for twice: not after a dry run, not after Anki rejected a note, not after a fatal error halfway through a run. Changing the model or `PROMPT_VERSION` misses the cache and pays again. The cache lives in the database file; deleting the database empties it.

**API prompt caching is not used.** The whole prompt is below the 512-token minimum Claude Opus 5.5 needs for a cache entry, and its first paragraph already contains the chunk key, so requests share no long prefix. Adding `cache_control` would cost a write premium with no reads.

## Logging

With `learn-german -v sync`, the adapter logs one line before each call (model, chunk, effort, prompt version, prompt length) and one after it (request ID, input and output tokens); `CachingProvider` logs each cache hit or miss. Request bodies, headers and the key are never logged ([0048](../decisions/0048-log-with-stdlib-logging-behind-a-global-verbose-flag.md)). Quote the request ID when reporting a problem to Anthropic.

## Testing

Tests never touch the network. `tests/integration/llm/mock_api.py` scripts replies behind `httpx2.MockTransport` and passes the mocked `httpx2.Client` to `AnthropicProvider.create(..., http_client=...)`. Error replies carry `retry-after-ms: 1`, so the SDK's real retry loop runs without sleeping. End-to-end tests pass the same client as `Overrides.llm_http_client`, so `sync` runs the real adapter (`tests/e2e/test_cli_verbose.py`).

The real API is exercised only by hand: the eval script below, the [release checklist](../development/release-checklist.md) and the [card quality measurement](../research/card-quality-v1.md).

## Manual evaluation

`tools/eval/run_eval.py` runs the prompt on the hand-written chunks in `tools/eval/chunks.tsv` against the real API and prints each chunk's content and sanity-check problems as one JSON line. It needs `ANTHROPIC_API_KEY`, costs a few cents per chunk, bypasses the cache, and refuses to run when `CI` is set:

```bash
uv run python tools/eval/run_eval.py [--model claude-opus-5-5] [--effort high]
```

Run it after a prompt or model change and read the cards before bumping `PROMPT_VERSION` for real use.

## Related

- [Generation](../system-design/generation.md)
- [Note types](../learning-design/note-types.md)
- [0004 Pluggable LLM provider](../decisions/0004-generate-card-content-through-a-pluggable-llm-provider.md)

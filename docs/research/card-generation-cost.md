---
title: Cost of card generation
summary: Measured cost of a 50-chunk sync on Opus 5.5, projected cost per card on other Claude models, budget tables, and how to compare models.
status: active
updated: 2026-11-27
---

# Cost of card generation

## Purpose

Gives the numbers needed to plan a budget for `sync`: what one card costs, what a month of cards costs at a chosen pace, and what the same work would cost on other Claude models. The Opus 5.5 figures are measured; the figures for other models are projections from the same token counts and must be checked before switching (see [Comparing models](#comparing-models)). How calls are made and billed is in [Claude API](../integrations/claude-api.md).

## Measurement

- **Date:** 2026-11-27
- **Run:** `run-20261127-1406`, `learn-german -v sync --cap 50`
- **Model and settings:** `claude-opus-5-5`, effort `medium`, prompt `card-v2`, no cache hits (first generation of every chunk)
- **Sources:** 40 current news articles (tagesschau.de, dw.com), 106 pending chunks before the run

| | Value |
|---|---|
| Claude calls | 50 |
| Notes added to Anki | 39 |
| Chunks that failed the checks | 11 (22 %) |
| Input tokens | 59,457 (about 1,190 per call) |
| Output tokens, thinking included | 24,870 (about 500 per call, 142 to 905) |
| Cost of the run | $0.74 (input $0.24, output $0.50) |
| Cost per call | $0.0147 |
| Cost per note added to Anki | $0.0189 |

Output is two thirds of the cost even though it is under half the tokens, because output tokens cost five times as much as input tokens. Most output is thinking, so the effort level drives the cost more than the prompt length does.

### Why 11 chunks failed

Failed calls are paid for and add nothing, so they raise the cost per card by the factor 50 / 39 ≈ 1.28.

- **10 were extraction errors.** The chunk key was not a real Nomen-Verb-Verbindung (for example `job|stellen`, `höhe|halten`, `check|geben`). Claude answered with the real expression from the sentence (*etwas auf den Prüfstand stellen*), which then failed the check that the citation form contains the key's noun and verb ([0036](../decisions/0036-check-card-content-then-cache-it-in-its-own-transaction.md)).
- **1 was a model error.** For `druck|ausüben` the shortened sentence had 14 words where at most 7 were allowed.

Failed answers are not cached and failed chunks stay pending, so every later `sync` pays for them again ([0014](../decisions/0014-keep-progress-when-a-run-fails-partway.md) has no retry limit yet). The figures below do **not** include these repeated retries. Until a retry limit exists, budget roughly one extra call per failing chunk per `sync` that picks it up.

## Cost per model

Projected from the measured averages (1,189 input and 497 output tokens per call, 39 notes per 50 calls). Prices are Anthropic first-party API rates per million tokens as of 2026-11; check the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing) before relying on them.

| Model | Input $/M | Output $/M | Per call | Per card | Per 100 cards |
|---|---|---|---|---|---|
| Claude Fable 5.1, Fable 5 | 10.00 | 50.00 | $0.0368 | $0.0471 | $4.71 |
| Claude Fable 5.2 | 8.00 | 40.00 | $0.0294 | $0.0377 | $3.77 |
| Claude Opus 5, 4.8, 4.7, 4.6 | 5.00 | 25.00 | $0.0184 | $0.0236 | $2.36 |
| **Claude Opus 5.5 (default, measured)** | **4.00** | **20.00** | **$0.0147** | **$0.0189** | **$1.89** |
| Claude Sonnet 4.6 | 3.00 | 15.00 | $0.0110 | $0.0141 | $1.41 |
| Claude Sonnet 5.5, Sonnet 5 | 2.00 | 10.00 | $0.0074 | $0.0094 | $0.94 |
| Claude Haiku 5.5 | 0.10 | 0.50 | $0.0004 | $0.0005 | $0.05 |

How far to trust the projections:

- **Thinking differs by model.** Each model thinks a different amount at `medium` effort, so the output tokens, two thirds of the cost, can be quite different from Opus 5.5's 497. This is the largest uncertainty.
- **Tokenizers differ.** Opus 4.7 and later, Opus 5, Opus 5.5 and the Fable models share one tokenizer, so their input counts should match. Opus 4.6 and Sonnet 4.6 use an older tokenizer that produces up to about 25 % fewer tokens for the same text, which makes their real cost somewhat lower than shown.
- **The failure rate differs.** A model that fails more checks costs more per card than its per-call price suggests. With these sources most failures were extraction errors, which no model can fix.
- **Not every model works.** The adapter sends structured outputs and an effort level ([0037](../decisions/0037-call-claude-with-a-json-schema-and-split-errors-into-fatal-and-item.md)). Claude Haiku 4.5 rejects the effort parameter and is left out. Check any model with `tools/eval/run_eval.py --model <id>` before switching.

## Budget

A card only helps once it is studied, and Anki shows a limited number of new cards per day (20 in the Default preset). Generating more cards than you study only builds a backlog, so plan the budget from your study pace:

| Pace | Cards per month | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 | Opus 5 |
|---|---|---|---|---|---|
| 5 new cards a day | 150 | $2.83 | $1.41 | $0.07 | $3.53 |
| 10 new cards a day | 300 | $5.66 | $2.83 | $0.14 | $7.07 |
| 20 new cards a day (Anki default) | 600 | $11.31 | $5.66 | $0.28 | $14.14 |

A year at 10 new cards a day (3,650 cards) costs about $69 on Opus 5.5, $34 on Sonnet 5.5 and under $2 on Haiku 5.5.

How often to run `sync` hardly affects the cost, because every chunk is paid for once no matter which run generates it. Pick the cap to match your pace: `sync` once a day with `--cap 10`, or once a week with `--cap 70`. The exception is failing chunks: each run retries them and pays again.

To protect the budget, set a monthly spend limit in the Claude Console. When the limit is reached, `sync` stops with an access error and keeps the notes already pushed ([Claude API](../integrations/claude-api.md)).

## Comparing models

The next step is to measure whether a cheaper model writes cards as good as Opus 5.5's. Cost alone does not decide it: a cheap model whose cards are often wrong costs study time, which is worth more than the cents saved. Measure quality and cost together, on the same chunks:

1. **Same chunks for every model.** A dry run pushes nothing, so the ranking stays the same and every model gets the same top chunks. The cache key includes the model, so each model really calls the API:

   ```bash
   LEARN_GERMAN_MODEL=claude-sonnet-5-5 learn-german -v sync --dry-run --cap 20 \
     > ~/cards-sonnet-5-5.txt 2> ~/cards-sonnet-5-5.log
   ```

   Repeat for each candidate, for example `claude-haiku-5-5` and `claude-opus-5-5` as the reference. Keep the files outside the repository ([0002](../decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md)).
2. **Cost.** Add up the input and output tokens from the `Claude answered for …` lines in each `.log` file and multiply by that model's prices. This replaces the projection above with a measured figure.
3. **Quality.** Grade every card with the rubric in [Card quality of v1](card-quality-v1.md), without knowing which model wrote it if possible. Count wrong notes and misleading notes per model.
4. **Failures.** Count the chunks each model fails, and why. With the current queue, the top 20 includes the 10 extraction errors from the measured run, which also shows how each model handles a key that is not an NVV.
5. **Effort.** For the cheapest model that comes close on quality, try `--effort low` and `--effort high` with `tools/eval/run_eval.py` as well, since effort changes the thinking tokens and with them most of the cost.

The cheapest model whose wrong-note count falls in the "keep" band of the card quality rubric is the candidate. Changing the default model is a decision: record it as a new decision record that supersedes the model part of [0015](../decisions/0015-set-v1-run-defaults.md).

## Related

- [Claude API](../integrations/claude-api.md)
- [Card quality of v1](card-quality-v1.md)
- [Configuration](../development/configuration.md)
- [0015 Set v1 run defaults](../decisions/0015-set-v1-run-defaults.md)
- [0014 Keep progress when a run fails partway](../decisions/0014-keep-progress-when-a-run-fails-partway.md)

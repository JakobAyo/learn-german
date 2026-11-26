---
title: Integrations
summary: External systems: Anki, translation, audio and any LLM; how each is called and fails.
---

# Integrations

External systems: Anki, translation, audio and any LLM; how each is called and fails.

## What belongs here

- Anki export through AnkiConnect into the running Anki app ([0003](../decisions/0003-push-notes-live-through-ankiconnect.md))
- Translation and text-to-speech providers for the back of the card
- Any LLM used to generate translations or transformation exercises: prompts, cost, rate limits
- Content sources' access methods and terms (news sites, subtitle downloads)

## What does not belong here

- Why one service was chosen over another (decisions/)
- Card content design (learning-design/)

<!-- docs-index:start -->

## Contents

- [AnkiConnect](ankiconnect.md) — How the Anki adapter talks to the running Anki app through AnkiConnect: setup, settings, actions used, failure modes, tests and the manual smoke test.
- [Claude API](claude-api.md) — How AnthropicProvider calls the Claude API: settings, request, retries, how each failure is reported, cost, mocked tests and the eval script.

<!-- docs-index:end -->

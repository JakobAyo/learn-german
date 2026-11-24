---
title: Structure the code as ports and adapters with a composition root
summary: Pure domain, use cases against Protocol ports, one adapter per external system, wired in one composition root; layering enforced by import-linter.
status: active
updated: 2026-11-24
---

# Structure the code as ports and adapters with a composition root

## Context

The requirements already name seven plug-in seams: sources, extractors, filters, rankers, LLM providers, Anki and storage (Deferred table in [Requirements](../product/requirements.md)). [0002](0002-build-a-single-user-python-cli-in-a-public-repo.md) asks for a library core under a thin CLI. CI must test without Anki, the API or the network (R28). The code needs one structure that makes all of this the default, not something each module has to remember.

## Decision

- Layers `domain` (pure), `application` (use cases), `ports` (`typing.Protocol`s), `adapters` (one per external system), `bootstrap` (composition root) and `cli` (thin typer commands). Details are in [Code architecture](../system-design/code-architecture.md).
- Dependencies point inward only. This is enforced by import-linter contracts in CI.
- Dependencies are injected through constructors in `bootstrap.py`. There is no DI framework, service locator or module-level singleton.
- Errors are split into `FatalError` (stop the run) and `ItemError` (record and continue), which puts [0014](0014-keep-progress-when-a-run-fails-partway.md) into the type system.
- LLM caching is a decorator around any provider, not part of an adapter.
- Every port has a hand-written fake that passes the same contract tests as the real adapter.

## Alternatives considered

- Flat modules per pipeline stage: rejected. Simpler at first, but nothing stops a stage from importing `httpx` or `anthropic` directly, and tests then need mocks everywhere.
- Abstract base classes for ports: rejected. Protocols give the same mypy checking without coupling adapters to an inheritance tree.
- A DI container (`dependency-injector`, `punq`): rejected. One composition root of a few dozen lines does the same job.
- Plug-in discovery through entry points: postponed until someone other than the owner writes plug-ins.

## Consequences

- A deferred feature is a new adapter plus one line in `bootstrap`.
- Use cases are tested with fakes in milliseconds.
- Slightly more files and indirection than a script would need. This is accepted, because the seams are requirements and not speculation.

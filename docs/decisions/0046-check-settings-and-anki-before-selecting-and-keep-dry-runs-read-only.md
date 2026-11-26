---
title: Check settings and Anki before selecting, and keep dry runs read-only
summary: sync checks hint language and API key while wiring, then sets Anki up before selecting; a dry run only checks Anki answers and writes only the LLM cache.
status: active
updated: 2026-11-26
---

# Check settings and Anki before selecting, and keep dry runs read-only

## Context

The roadmap's M7 asks for a preflight before any money is spent: hint language set, API key present, Anki reachable and set up, each failure fatal. In `--dry-run`, an unreachable Anki is only a warning and deduplication against Anki is skipped ([0033](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)). R23 says a dry run writes nothing to Anki, yet `ensure_setup` creates the deck and note types, and the `AnkiGateway` port had no call that only asks whether Anki answers. The hint language and the key are settings, which only `bootstrap` and `cli` may read ([0018](0018-structure-code-as-ports-and-adapters.md)). M3's commands get their plug-ins from `bootstrap` with test `Overrides` ([0045](0045-build-the-cli-with-create-app-and-stream-outcomes.md)).

## Decision

- **Settings are checked while wiring.** `bootstrap.sync_service(settings, overrides)` first calls `settings.require_hint_language()` (R16, [0015](0015-set-v1-run-defaults.md)), then builds the provider, which needs its API key, and only then opens the database. A dry run needs both too, since it generates.
- **Providers come from a registry.** `bootstrap.LLM_PROVIDERS` maps the `provider` setting to a factory that checks its own credentials; v1 has only `anthropic`. An unknown name is a `ConfigError` listing the known ones. `Overrides.provider` replaces the inner provider in tests, and is still wrapped as `CachingProvider(CheckedProvider(provider), uow, clock)` ([0036](0036-check-card-content-then-cache-it-in-its-own-transaction.md)), so tests exercise the real checks and cache.
- **Anki is checked in `SyncService.start`, before selection.** A real run calls `ensure_setup`, so an unreachable Anki or a mismatched note type stops it with exit 2 before any LLM call.
- **`AnkiGateway.check_available()`** is added to the port: it asks AnkiConnect for its version and changes nothing. A dry run calls it instead of `ensure_setup`. If it raises `AnkiUnavailableError`, the run warns on stderr and selects with an empty `FilterChain`, so deduplication rests on `pushed_notes` alone. Any other fatal error still stops a dry run.
- **A dry run is read-only apart from the cache.** It writes nothing to Anki, not even the deck or note types, and records no pushed notes or chunk errors. Generated content is cached as in a real run, so the following `sync` does not pay again (R23).

## Alternatives considered

- **Call `ensure_setup` in a dry run too:** simpler, but creates a deck and two note types in a collection the user only wanted to preview.
- **Probe Anki with `existing_keys` in a dry run:** works without a port change, but hides the intent, and a dry run against a reachable Anki calls the filter anyway.
- **Check the hint language and key inside `SyncService`:** the application layer may not import `config`, and the messages need to name the config file and environment variables, which only `config` knows.
- **Check the key lazily, at the first LLM call:** a missing key would surface only after Anki was set up and chunks selected, and an override-free test could not show that nothing was asked first.

## Consequences

- The order of failures is fixed: settings (hint language, then provider and key), database, Anki, then selection. Tests assert that each stops before any LLM call.
- A dry run with Anki reachable shows exactly what a real run would add; without Anki it may show notes Anki already has, and says so.
- Recording errors only in real runs means a dry run's failures are shown but not remembered.
- Every `AnkiGateway` implementation needs `check_available`; the contract suite covers it.

## Related

- [Pipeline](../system-design/pipeline.md)
- [0047 Push a chunk's notes one call each and save progress per chunk](0047-push-notes-one-call-each-and-save-progress-per-chunk.md)
- [0040 Add notes one call each](0040-add-notes-one-call-each-and-split-ankiconnect-errors.md)

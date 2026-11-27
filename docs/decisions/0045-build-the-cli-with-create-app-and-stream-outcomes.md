---
title: Build the CLI with create_app and stream outcomes per source
summary: create_app takes bootstrap Overrides so tests swap plug-ins; use cases yield one outcome per source, printed at once by presenters; exit codes 0, 1 and 2.
status: active
updated: 2026-11-26
---

# Build the CLI with create_app and stream outcomes per source

## Context

M3 adds the first commands that do real work. The [Testing strategy](../development/testing-strategy.md) wants end-to-end tests through typer's `CliRunner` with fakes injected through `bootstrap`, the [Coding conventions](../development/coding-conventions.md) want output only in `cli/presenters.py`, and the error model wants a fatal error to stop at once while showing what was done ([Code architecture](../system-design/code-architecture.md#error-model)). `add` on many URLs can take a while, so waiting for the end before printing anything is poor feedback.

## Decision

- **`create_app(overrides)` builds the typer app.** The module-level `app` is `create_app()`. `bootstrap.Overrides` names the plug-ins a test may replace (clock, extractors, source adapters, the HTTP client); `None` builds the real one. No module-level state is patched.
- **`bootstrap.ingest_services(settings, overrides)`** is a context manager that opens the database, wires `AddSources`, `ShowStatus` and `Reextract`, and closes the connection and the HTTP client on exit. M7 adds the `sync` wiring next to it.
- **Use cases yield outcomes.** `AddSources.run` and `Reextract.run` are iterators that yield one outcome per source after its unit of work has committed. The CLI prints each line as it arrives, so a fatal error halfway leaves the lines of finished sources on screen, and their data in the database.
- **One error boundary per command** turns any `FatalError`, including invalid settings and a missing spaCy model, into `Error: <message>` on stderr and exit code 2.
- **Exit codes:** 0 when everything worked (skipped sources included), 1 when at least one source failed, 2 for a fatal or usage error, matching typer's own code for usage errors.
- **`status`** lists the five most recent sources and the top ten pending chunks (`--top N`), ranked by `OccurrenceRanker` without asking Anki.
- **`add --from FILE`** reads one reference per line, skipping blank lines and lines starting with `#`. Relative paths in it resolve against the working directory, like paths on the command line.

## Alternatives considered

- **Patch `bootstrap` functions in tests with monkeypatch:** works, but ties tests to private names and hides what can be replaced.
- **Return a full report at the end:** simpler types, but no output until every URL is fetched, and nothing printed when a fatal error comes late.
- **A callback argument for progress:** same effect as an iterator, with one more parameter on every use case.
- **Resolve `--from` paths against the list file's folder:** convenient for a list kept next to its files, but surprising next to how command-line paths behave.

## Consequences

- Use cases that write per item follow the same shape in M7: open a unit of work per item, yield after commit.
- The CLI module holds no logic beyond argument checks; formatting is unit-tested in `tests/unit/cli/`.

## Related

- [Ingest](../system-design/ingest.md)
- [0018 Structure the code as ports and adapters](0018-structure-code-as-ports-and-adapters.md)
- [0014 Keep progress when a run fails partway](0014-keep-progress-when-a-run-fails-partway.md)

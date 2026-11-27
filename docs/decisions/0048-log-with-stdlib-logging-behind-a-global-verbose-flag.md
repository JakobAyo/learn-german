---
title: Log with stdlib logging behind a global --verbose flag
summary: A global --verbose/-v option turns on DEBUG for the learn_german loggers only, on stderr; third-party loggers stay at WARNING and a filter masks API keys.
status: active
updated: 2026-11-26
---

# Log with stdlib logging behind a global --verbose flag

## Context

M8 asks for `--verbose` logging so that a failing run can be understood without a debugger. The modules already use a module-level `logging` logger ([Coding conventions](../development/coding-conventions.md)), but nothing configured logging, so only Python's last-resort handler printed warnings. User-facing output goes through `cli/presenters.py` on stdout; debug output must not mix with it. The run talks to three outside systems (news sites, the Claude API, AnkiConnect), and the Anthropic API key must never reach the terminal or a pasted log ([0002](0002-build-a-single-user-python-cli-in-a-public-repo.md)).

## Decision

- **One global option**, `learn-german --verbose` (short `-v`), given before the command. It is a typer callback option, so every command has it.
- **stdlib `logging` only.** `cli/logs.py` installs one handler on the root logger that writes to the current `sys.stderr`. Without the flag the root level is WARNING, as Python's default; with it the `learn_german` logger is set to DEBUG. Format: `LEVEL: message`, and `LEVEL logger.name: message` when verbose.
- **Third-party loggers stay at WARNING** even with `--verbose`. httpx2, httpcore and the Anthropic SDK log request details at DEBUG, which is where headers would leak; their warnings still show.
- **What is logged, at the I/O boundaries:** settings files read; database opened and migrations; each web GET and its status and size, robots.txt reads and refusals, words extracted; occurrences per extractor; source skips; chunks selected, filtered and capped, and the picked sentence; LLM cache hit or miss; each Claude call (model, chunk, effort, prompt version, prompt length) and its request ID and token counts; each AnkiConnect action answered or failed, deck and note types created, keys read, notes added.
- **Never logged:** the API key, request headers, request bodies, or whole settings objects. As a backstop, a `RedactSecrets` filter on the handler replaces anything matching `sk-ant-…` in messages and tracebacks.
- An e2e test runs `-v sync` through the real Claude adapter and the real Anki gateway over mocked HTTP and asserts the debug lines appear and the key does not.

## Alternatives considered

- **A `--log-level` option or a `LEARN_GERMAN_LOG_LEVEL` setting:** more flexible, but one user needs only "quiet" and "everything of ours"; a level can be added later without breaking `-v`.
- **structlog or rich logging:** extra dependencies for a single-user CLI whose log is read in a terminal.
- **Logging to a file:** state lives in SQLite already; `2> run.log` is enough when a log has to be kept.
- **Turning on third-party DEBUG with `-vv`:** the SDK's own `ANTHROPIC_LOG=debug` already exists for that rare case, and keeping it out of our flag keeps the no-secrets promise simple.

## Consequences

- Warnings from any library (for example trafilatura) still reach stderr without `--verbose`, now with a `WARNING:` prefix.
- `--verbose` goes before the command (`learn-german -v sync`); after it, typer reports an unknown option.
- Tests restore the root logger after each test, because every CLI invocation configures logging.
- `bootstrap.Overrides` gained `llm_http_client`, so tests can run the real Claude adapter over a mocked transport, as `anki_http_client` does for Anki.

## Related

- [Coding conventions](../development/coding-conventions.md)
- [Claude API](../integrations/claude-api.md)
- [AnkiConnect](../integrations/ankiconnect.md)

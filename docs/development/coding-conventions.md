---
title: Coding conventions
summary: Typing, naming, error handling, I/O boundaries, configuration and pull-request rules that every change follows.
status: draft
updated: 2026-11-26
---

# Coding conventions

## Purpose

Rules that keep the code consistent and easy to change. Anything a tool can check is checked in CI (see [CI and releases](ci-and-releases.md)). This page lists what the tools cannot check. Read it before opening a pull request.

## Types and data

- `mypy --strict` passes on `src/` and `tests/`. No `Any` in `domain/` or `application/`; `# type: ignore` needs an error code and a reason.
- Ports are `typing.Protocol`s. Domain data is `@dataclass(frozen=True, slots=True)`.
- pydantic appears only at boundaries (settings, LLM output). Adapters convert pydantic models to domain dataclasses before returning.
- Enums for closed sets (chunk kind, candidate status), never bare strings.

## Structure

- Name modules after a concept (`occurrence.py`, `news_url.py`). No `utils.py`, `helpers.py` or `common.py`.
- Keep logic in pure functions and I/O at the edges. A function either decides or does I/O, not both.
- Keep functions short enough to read without scrolling. A long function is a sign that a value object or helper is missing.
- Never read `os.environ` outside `config.py`. Read settings once in `bootstrap` and pass values into constructors.
- Time, randomness and paths are injected (`Clock`, settings), never taken from globals inside logic.
- Load data files (light verbs, spelling variants, prompts, templates) through `importlib.resources`, never relative to the working directory.

## Errors and output

- Adapters wrap third-party exceptions in a `FatalError` or `ItemError` subclass with `raise … from exc`. See the error model in [Code architecture](../system-design/code-architecture.md#error-model).
- No bare `except:`, and no `except Exception` outside the CLI's top-level handler.
- User-facing output goes only through `cli/presenters.py`. Everything else uses `logging` with a module-level logger. No `print` outside `cli/`.
- Log at the I/O boundaries: DEBUG for each request and its outcome, INFO for what changed (a deck created, words extracted), WARNING for something the user should fix. `--verbose` shows DEBUG and INFO ([0048](../decisions/0048-log-with-stdlib-logging-behind-a-global-verbose-flag.md)). Never log an API key, request headers, request bodies or a whole settings object.
- Every error message tells the user what to do next (*Start Anki with AnkiConnect enabled*, *Save the article as .txt and run `add file.txt`*).

## Comments and docstrings

- Docstrings on every port, use case and public adapter class: what it does and what it raises.
- Comments explain why, not what. Link the requirement or decision when it explains a rule (`# R11: dedupe per note type`).

## Public repository rules

From [0002](../decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md): no API keys, personal paths, personal config, mined sentences or copied articles, including in tests, fixtures and examples. Fixtures are hand-written German. Secret scanning with push protection is a backstop, not the main defence.

## Pull requests

- One concern per PR. Squash-merged; the PR title is the commit message and must follow [Conventional Commits](ci-and-releases.md#commit-and-pr-title-convention).
- Tests for new behaviour come in the same PR.
- A behaviour change updates its doc. A new choice gets an ADR in `docs/decisions/`.
- `make check` passes locally before pushing.

## Related

- [Code architecture](../system-design/code-architecture.md)
- [Testing strategy](testing-strategy.md)
- [CI and releases](ci-and-releases.md)

---
title: Parallel tracks
summary: File ownership of the parallel tracks M2, M4, M5 and M6, frozen files, reserved decision numbers, and the path from worktree to main.
status: active
updated: 2026-11-26
---

# Parallel tracks

## Purpose

M2, M4, M5 and M6 are built at the same time by separate agents, each in its own git worktree ([0026](../decisions/0026-run-m2-m4-m5-m6-as-parallel-tracks.md)). This page is the contract between them. Every agent reads it before its first edit. When a track needs a file it does not own, it stops and asks the owner instead of editing.

## Tracks

| Track | Branch | Worktree | Decisions |
|---|---|---|---|
| M2 NVV extractor | `feat/m2-nvv-extractor` | `../learn-german-tracks/m2-nvv-extractor` | 0029 to 0031 |
| M4 Selection | `feat/m4-selection` | `../learn-german-tracks/m4-selection` | 0032 to 0034 |
| M5 Generation | `feat/m5-generation` | `../learn-german-tracks/m5-generation` | 0035 to 0037 |
| M6 Anki export | `feat/m6-anki-export` | `../learn-german-tracks/m6-anki-export` | 0038 to 0040 |

Worktree paths are relative to the main checkout. Unused decision numbers stay unused.

## File ownership

A track may create and edit files only under its own paths. Paths are relative to the repository root.

**M2 NVV extractor**

- `src/learn_german/adapters/nlp/**`: parse, match, key builder, `NvvExtractor`, data files (`light_verbs.txt`, `spelling_variants.tsv`)
- `src/learn_german/bootstrap.py`: the extractor registry only
- `tests/unit/nlp/**`, `tests/nlp/**`, `tests/data/nlp/**` (golden corpus)
- `.github/workflows/ci.yml` (the `nlp` job), `Makefile` (a `test-nlp` target)
- `docs/system-design/nvv-extraction.md` (new); the `nlp` rows in `docs/development/setup.md` and `docs/development/ci-and-releases.md`

**M4 Selection**

- `src/learn_german/application/selection/**`: `FilterChain`, `AlreadyInDeckFilter`, `OccurrenceRanker`, cap, `OccurrencePicker`
- `src/learn_german/ports.py`: methods inside `CandidateRepository` and `ChunkStateRepository`, and new protocols added after `Clock`, before the storage section
- `src/learn_german/adapters/storage/**`, including migrations from `0002_` on
- `tests/unit/selection/**`, `tests/contract/test_storage.py`, `tests/integration/test_sqlite_database.py`
- `docs/data/data-model.md`, `docs/system-design/pipeline.md`

**M5 Generation**

- `src/learn_german/adapters/llm/**`: `AnthropicProvider`, pydantic output schema, prompt template files, `PROMPT_VERSION`
- `src/learn_german/application/generation/**`: prompt rendering, `CachingProvider`, sanity checks
- `src/learn_german/ports.py`: the body of `LLMProvider` only
- `tests/fakes/llm.py`, `tests/unit/generation/**`, `tests/integration/llm/**`, `tests/data/llm/**`
- `tools/eval/**`
- `docs/integrations/claude-api.md`, `docs/system-design/generation.md` (new)

**M6 Anki export**

- `src/learn_german/adapters/anki/**`: `AnkiConnectClient`, `AnkiConnectGateway`, `NoteTypeSpec`, templates and CSS
- `src/learn_german/application/notes/**`: `NoteBuilder`, tag builder
- `tests/fakes/anki.py`, `tests/contract/test_anki_gateway.py`, `tests/unit/notes/**`, `tests/integration/anki/**`, `tests/data/anki/**`
- `docs/integrations/ankiconnect.md`, `docs/learning-design/note-types.md`

## Frozen files

Changed only with the owner's agreement, usually as a separate small PR that every track then merges:

- `pyproject.toml`, `uv.lock`: dependencies, tool config, pytest markers
- `src/learn_german/domain/**`: `CardRequest`, `CardContent`, `NoteDraft`, `PendingChunk`, errors. A track that needs its own error defines a subclass of a domain error inside its own package.
- `src/learn_german/config.py`, `src/learn_german/cli/**`
- `tests/conftest.py`, `tests/fakes/clock.py`
- `docs/product/**`, `docs/system-design/code-architecture.md`: list needed changes in the PR description; they are applied after the tracks merge.

## Shared rules

- **Imports:** adapters never import each other, and `domain`, `ports` and `application` import no I/O library (import-linter enforces both). Use `httpx2`, not `httpx` ([0027](../decisions/0027-settle-shared-dependencies-before-parallel-tracks.md)).
- **Fakes:** depend on neighbours only through ports and the shared fakes `FakeAnkiGateway` and `FakeProvider` in `tests/fakes/`. Do not import another track's code.
- **Fixtures:** put fixtures in a `conftest.py` inside your own test folder, not in `tests/conftest.py`.
- **Generated indexes:** the `docs-index` sections of every `CLAUDE.md` are generated. On a merge conflict there, take either side and run `python3 tools/docs/build_index.py --docs-root docs`.
- **Done means `make check` passes** in the worktree, with tests for every new behaviour.

## From worktree to main

1. Commit in small Conventional Commits on the track branch. Agents do not push.
2. Before the PR, run `git fetch origin && git merge origin/main`, resolve conflicts (only generated indexes should conflict), and run `make check` again.
3. The owner pushes the branch and opens one PR into `main`, titled `feat: …` with the milestone in it, for example `feat: add NVV extractor (M2)`.
4. After the squash merge, the owner syncs `develop` (`git checkout develop && git pull && git merge origin/main && git push`), and every other open track merges `origin/main` again.

## Related

- [Roadmap](../product/roadmap.md)
- [Code architecture](../system-design/code-architecture.md)
- [CI and releases](ci-and-releases.md)

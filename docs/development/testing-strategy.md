---
title: Testing strategy
summary: Test layers from pure unit to manual release checks, fakes and contract tests, the no-network and synthetic-fixture rules, and coverage targets.
status: draft
updated: 2026-11-26
---

# Testing strategy

## Purpose

States what is tested at which layer and with which doubles, so tests stay fast, need no secrets or Anki (R28), and catch the bugs that matter for this tool: wrong chunk keys, duplicate notes, paying twice, and lost progress. Read this before writing a test.

## Layers

| Layer | What | Doubles | Folder | CI job |
|---|---|---|---|---|
| Unit | Domain rules, pure functions, use cases | Fakes from `tests/fakes/` | `tests/unit/` | `test` |
| Contract | Every implementation of a port and its fake pass one shared suite | None (that is the point) | `tests/contract/` | `test` |
| Integration | SQLite on a temp file, migrations; HTTP adapters against `httpx2.MockTransport` | Mocked transport only | `tests/integration/` | `test` |
| NLP | Real `de_core_news_lg`: the 0011 key table and the golden corpus | None | `tests/nlp/` (marker `nlp`) | `nlp` |
| End to end | CLI commands through typer's `CliRunner`, real SQLite, fake LLM, Anki, extractor | Fakes passed as `bootstrap.Overrides` to `create_app` | `tests/e2e/` | `test` |
| Manual | Real Anki and the real Claude API | None | [Release checklist](release-checklist.md) | not in CI |

## Rules

- **Fakes over mocks.** Each port has one hand-written fake in `tests/fakes/` (for example `FakeAnkiGateway` holds an in-memory deck). A fake passes the same contract suite as the real adapter, so tests that use it can be trusted. `unittest.mock` is a last resort.
- **No network.** `pytest-socket` disables sockets for every test. HTTP adapters get an `httpx2.MockTransport` ([0027](../decisions/0027-settle-shared-dependencies-before-parallel-tracks.md)).
- **No real home directory or secrets.** An autouse fixture points HOME and the XDG directories at `tmp_path`, runs each test in an empty working directory (so a developer's `.env` is never read) and removes every `LEARN_GERMAN_*` and `ANTHROPIC_*` variable.
- **Synthetic fixtures only.** German sentences and HTML pages are written by hand for the test. Never paste a real article (R28, 0002).
- **Deterministic.** Run IDs come from `FixedClock`; ordering ties are broken explicitly; no sleeps.
- **One behaviour per test**, named `test_<unit>_<behaviour>`, laid out as arrange, act, assert. Tables of cases use `pytest.mark.parametrize` with readable `ids`.
- **Golden files** for the rendered prompt and card templates live next to their tests. Update them on purpose, never automatically in CI.

## Guards for things that are expensive to get wrong

| Risk | Guard |
|---|---|
| Chunk key format drifts, which breaks deduplication for good (0011) | Unit tests on the key builder; NLP tests on every 0011 row |
| Extractor change silently loses NVVs | Golden-corpus precision and recall must not drop below the recorded baseline |
| Note type fields change without a migration (0003) | Frozen spec test asserts v1 field names and order literally |
| Prompt changes but the cache serves old output (0004) | Template hash recorded per `PROMPT_VERSION`; a mismatch fails |
| Duplicate notes on re-run (R11) | E2E: running `sync` twice adds nothing; missing second note is created alone |
| Progress lost on failure (0014) | E2E: one failing chunk leaves the others pushed and itself pending with its error |
| Money spent before a fatal error | E2E: Anki unreachable or missing hint language stops before any LLM call |
| A fetch ignores robots.txt (0013) | Integration test asserts a disallowed article URL is never requested |
| Re-adding or re-extracting loses note history (0017) | The four reextract rules as one parametrised test; `--force` follows the same rules |
| A layer imports an adapter | import-linter contracts in CI |

## Coverage

Branch coverage with `fail_under = 85` on `src/`, measured by the `test` job. `nlp` tests are not counted, so the number does not depend on the model. Protocol bodies and `if TYPE_CHECKING:` blocks are excluded. The threshold catches untested new modules; it is not a target to chase.

## Tooling

`pytest`, `pytest-cov` and `pytest-socket`. There is no property-based testing library: the key builder is covered by parametrised tables instead. HTTP is mocked with `httpx2.MockTransport`, so no extra mocking library is needed.

## Related

- [Code architecture](../system-design/code-architecture.md)
- [CI and releases](ci-and-releases.md)
- [Roadmap](../product/roadmap.md)

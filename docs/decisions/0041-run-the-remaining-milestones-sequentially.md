---
title: Run the remaining milestones one at a time on branches off develop
summary: With the parallel tracks merged, M3, M7 and M8 are built one after another on branches off develop; file ownership and frozen files no longer apply.
status: active
updated: 2026-11-26
---

# Run the remaining milestones one at a time on branches off develop

## Context

M2, M4, M5 and M6 ran as parallel tracks under [0026](0026-run-m2-m4-m5-m6-as-parallel-tracks.md) and are merged into `develop`. The milestones left, M3, M7 and M8, depend on each other in that order ([Roadmap](../product/roadmap.md)): M7 wires `sync` on top of the ingest and `bootstrap` work of M3, and M8 hardens what M7 delivers. They also touch the files that 0026 froze, chiefly `cli/`, `bootstrap.py`, `config.py` and the domain. Running them in parallel would gain little and bring the coordination cost back.

## Decision

- M3, M7 and M8 are built one at a time, in that order, each on its own branch off the current `develop` in the main checkout. No worktrees.
- The file ownership, frozen files and reserved decision numbers of [Parallel tracks](../development/parallel-tracks.md) no longer apply. A milestone edits whatever it needs, under the usual rules: tests ship with the code, docs and decisions move with it.
- A finished milestone is merged into `develop` with `--no-ff`, as under 0026, and `develop` goes to `main` as in [0022](0022-keep-a-long-lived-develop-branch.md). When several milestones are on `develop` since the last release, the PR body still lists one Conventional Commit line per milestone in a `BEGIN_COMMIT_OVERRIDE` block.
- The Parallel tracks page stays as a record of how M2, M4, M5 and M6 were built, marked deprecated.

## Alternatives considered

- **Keep running parallel tracks for M3 and M7:** M7 needs M3's wiring, so the second track would wait or build against guesses, and both would contend for the frozen files.

## Consequences

- Shared files change in the milestone that needs them, without a separate prep commit.
- Decision numbers are taken in order from 0041 on.

## Related

- [0026 Run M2, M4, M5 and M6 as parallel tracks](0026-run-m2-m4-m5-m6-as-parallel-tracks.md)
- [Parallel tracks](../development/parallel-tracks.md)
- [Roadmap](../product/roadmap.md)

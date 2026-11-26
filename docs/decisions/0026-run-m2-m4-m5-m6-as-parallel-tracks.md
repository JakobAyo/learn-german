---
title: Run M2, M4, M5 and M6 as parallel tracks with file ownership
summary: Four agents build M2, M4, M5 and M6 at once in worktrees; each track owns fixed files, shared contracts are frozen, each merges into main alone.
status: active
updated: 2026-11-26
---

# Run M2, M4, M5 and M6 as parallel tracks with file ownership

## Context

After M1 the [Roadmap](../product/roadmap.md) lets M2, M4, M5 and M6 proceed independently, each against fakes of its neighbours. The owner wants four coding agents to build them at the same time. Four branches off the same base collide wherever they touch the same lines: the lock file, the domain types they share (`CardContent` sits between M5 and M6), the error hierarchy, settings, the shared fakes, decision numbers and the generated docs indexes. Conflicts found at merge time are expensive, because an agent resolving them does not know the other track's intent.

## Decision

- **Settle shared things first, in one prep commit.** Runtime dependencies for all four tracks and the spaCy model extra ([0027](0027-settle-shared-dependencies-before-parallel-tracks.md)), the `citation_form` field on `CardContent` ([0028](0028-let-the-llm-supply-the-citation-form.md)), the error classes the tracks need, the `anki_connect_url` setting, and the shared `FakeAnkiGateway` and `FakeProvider`.
- **One worktree and branch per track:** `feat/m2-nvv-extractor`, `feat/m4-selection`, `feat/m5-generation`, `feat/m6-anki-export`, each in its own directory with its own `.venv`.
- **Every file has one owner.** A track edits only the files listed for it in [Parallel tracks](../development/parallel-tracks.md). Files listed as frozen change only after the owner agrees; a track that needs such a change stops and asks.
- **Reserved decision numbers.** M2 uses 0029 to 0031, M4 0032 to 0034, M5 0035 to 0037, M6 0038 to 0040. Unused numbers stay as gaps, which the docs validator reports only as a warning. The next free number after the tracks is 0041.
- **Each track merges into `main` on its own.** Its branch is proposed straight to `main` as one squash-merged PR with a `feat:` title, so each milestone gets its own changelog entry. `main` is merged back into `develop` after each merge ([0022](0022-keep-a-long-lived-develop-branch.md)). Before its PR, a track merges `origin/main` and reruns `make check`.
- **Generated index conflicts are regenerated, not hand-merged.** Run `python3 tools/docs/build_index.py --docs-root docs`.
- **Wiring waits for M3 and M7.** No track wires its adapters into `bootstrap.py` or the CLI, except the M2 extractor registry.

## Alternatives considered

- **One track at a time:** no coordination cost, but about four times the wall-clock time.
- **Feature branches into `develop`, then one `develop` → `main` PR:** keeps `develop` as the integration point, but one squash commit for four milestones collapses them into one changelog entry.
- **Let each track add its own dependencies:** each change rewrites `uv.lock`, so every later merge conflicts in the lock file.

## Consequences

- Contract changes after the prep commit are slower: they go through the owner and a new ADR.
- Some docs that every track would touch, chiefly the port table in [Code architecture](../system-design/code-architecture.md), are updated once after the tracks merge. Each PR lists what it needs changed there.
- `develop` may lag behind `main` while tracks merge; the sync rule from 0022 brings it back.

## Related

- [Parallel tracks](../development/parallel-tracks.md)
- [0023 Release as features land](0023-release-as-features-land.md)
- [0018 Ports and adapters](0018-structure-code-as-ports-and-adapters.md)

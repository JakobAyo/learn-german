---
title: Release as features land, not once per milestone
summary: M2 to M6 run as parallel tracks after M1, so 0.x versions count up as features merge and no longer map to milestones; 1.0.0 stays tied to M8.
status: active
updated: 2026-11-25
---

# Release as features land, not once per milestone

## Context

The [Roadmap](../product/roadmap.md) lets four tracks run in parallel after M1: M2 then M3, M4, M5 and M6. Each one is built against fakes of the others. The roadmap also said "one release per milestone" and gave each milestone a fixed version (M1 = 0.2.0 … M7 = 0.8.0), and [0020](0020-version-with-conventional-commits-and-release-please.md) says the release PR is merged once per milestone.

Both rules cannot hold together. release-please collects every `feat:` that reaches `main` into its one open release PR. If M4, M5 and M6 work merges in the same period, the next release contains parts of all three, whichever milestone it is named after.

## Decision

- **Versions count up as features land.** A 0.x minor version means "new features since the last release", not "milestone N is done". Milestone names are labels for planning only.
- **Cadence:** merge the release PR when any milestone's done-when check passes, or earlier for an urgent fix. A release may also contain finished parts of other tracks.
- **Unfinished work stays unreachable.** Code from a track still in progress may ship in a release as long as no CLI command exposes it. Only wired, finished commands are user-visible.
- **1.0.0 stays tied to M8.** It is still forced with a `Release-As: 1.0.0` footer when M8 is done.
- This replaces the "merged once per milestone" bullet of 0020. The rest of 0020 still applies.

## Alternatives considered

- **Long-lived branch per milestone, merged into `main` in order:** keeps the version-to-milestone mapping, but brings the serial order back at merge time and leaves several branches to keep in sync with `main`, on top of `develop` ([0022](0022-keep-a-long-lived-develop-branch.md)).
- **Build in parallel, release in order:** merge M4's PRs, release, then M5's, and so on, while the other tracks wait in open PRs. That keeps the mapping, but finished work waits, and the waiting PRs go stale and conflict.

## Consequences

- The roadmap no longer lists a version per milestone. The `CHANGELOG.md` and GitHub Releases show what each version contains.
- Each `develop` → `main` PR becomes one squash commit and one changelog line. Keep those PRs to one concern, as the PR template already asks, so parallel tracks don't blur into a single line.
- Parallel tracks only work if M1 fixes the shared ports and schema completely. Four coupling points must be settled there:
  - `CardContent` and `CardRequest`: used by both M5 and M6, so they belong in `domain/`.
  - An optional citation-form field in `CardContent`: needed in case M2 cannot derive the article from the parse.
  - The candidate sentence and context columns: read by M4's occurrence picker.
  - `status`: it reuses M4's ranker but ships in M3, so it is built after M4 or moves to M7.

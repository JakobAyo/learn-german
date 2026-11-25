---
title: Version with Conventional Commits and release-please
summary: Conventional Commit PR titles drive SemVer; release-please keeps a release PR that bumps pyproject.toml and CHANGELOG.md and tags on merge.
status: active
updated: 2026-11-25
---

# Version with Conventional Commits and release-please

## Context

The owner wants automatic versioning and a changelog. The tool is installed from git tags, not from PyPI. PRs are squash-merged, so each PR title becomes exactly one commit on `main`.

## Decision

- Semantic Versioning. 0.x through M7, 1.0.0 at M8 ([Roadmap](../product/roadmap.md)).
- PR titles follow Conventional Commits, checked in CI. `feat` bumps the minor version, `fix` and `perf` the patch version, and `!` or `BREAKING CHANGE` the major version (minor before 1.0.0). Chunk key format changes, new note type versions and non-automatic DB migrations count as breaking.
- release-please (`release-type: python`) keeps one release PR that bumps `pyproject.toml`, updates `uv.lock` and writes `CHANGELOG.md`. Merging it creates the tag and a GitHub Release.
- The release PR is merged once per milestone. *Replaced by [0023](0023-release-as-features-land.md): versions count up as features land.*
- release-please uses a fine-grained token limited to this repository, so the release PR triggers the required checks.

Details, config and the two M0 pitfalls are in [CI and releases](../development/ci-and-releases.md).

## Alternatives considered

- python-semantic-release: releases on every merge by committing to `main` directly, which conflicts with branch protection and gives no point to batch a milestone.
- commitizen (`cz bump`): works well but is run by hand, so it is not automatic.
- Hand-written changelog and tags: easy to forget, which is the problem being solved.
- Version from git tags (`hatch-vcs`): avoids the `uv.lock` bump but makes the version invisible in the source and complicates installs from a branch.

## Consequences

- The changelog is only as good as the PR titles, so the title check is a required job.
- One repository secret exists, used only by the release workflow.
- The existing non-conventional commits stay as they are; the first changelog section starts at 0.1.0.

---
title: Keep a long-lived develop branch
summary: develop is a protected integration branch that survives merges; after each squash merge into main, main is merged back into develop.
status: active
updated: 2026-11-25
---

# Keep a long-lived develop branch

## Context

The repository is set to delete head branches after merge ([CI and releases](../development/ci-and-releases.md#repository-settings)). When PR #1 (`develop` → `main`) was squash-merged, GitHub deleted `develop` too. The owner wants `develop` kept as a standing integration branch, while short-lived branches should still be cleaned up.

Squash merges cause a second problem. `main` gets one new commit, but `develop` keeps its original commits, so the next `develop` → `main` PR would show already-merged changes again or conflict.

## Decision

- **`develop` is permanent.** It is protected against deletion and force pushes. GitHub does not auto-delete a protected head branch, so "delete branches after merge" stays on for every other branch.
- **Direct pushes to `develop` are allowed.** It needs no PR or required checks. CI runs when it is proposed to `main`.
- **Sync after every merge into `main`.** After a `develop` → `main` squash merge, and after a release-please PR merges, merge `main` back into `develop` (`git checkout develop && git pull && git merge origin/main && git push`). That moves the merge base to the squash commit, so the next PR shows only new work. Force pushes are not needed.
- **Recreated at the M0 squash commit.** After the accidental deletion, `develop` was recreated at `8b50258` (the M0 squash commit on `main`), whose tree matched the old `develop` exactly.

## Alternatives considered

- **Turn off "delete branches after merge" globally:** keeps `develop`, but leaves every other merged branch behind to clean up by hand.
- **Reset `develop` to `main` after each merge:** gives cleaner history, but needs force pushes, which would also leave `develop` unprotected against a mistaken force push.
- **Drop `develop` and branch every change off `main`:** the usual squash-merge pattern, but not what the owner wants.

## Consequences

- `develop` collects merge commits from `main`. They never reach `main`, because each PR is squashed into one commit.
- Forgetting the sync makes the next PR show old changes again or conflict. The fix is to run the sync, not to force push.
- Branch protection on `develop` is a repository setting applied by hand, listed in [CI and releases](../development/ci-and-releases.md#repository-settings).

## Related

- [0019 Gate main with required CI checks and branch protection](0019-gate-main-with-ci-checks.md)
- [0020 Version with Conventional Commits and release-please](0020-version-with-conventional-commits-and-release-please.md)

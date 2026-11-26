---
title: CI and releases
summary: CI jobs that gate main, repository settings, the Conventional Commits PR-title rule, and how release-please produces versions, tags and CHANGELOG.md.
status: draft
updated: 2026-11-26
---

# CI and releases

## Purpose

Describes how a change gets from a branch to `main` and from `main` to a versioned release. Every job is meant to catch a real class of bug; anything that would only add noise has been left out. The decisions are [0019](../decisions/0019-gate-main-with-ci-checks.md) and [0020](../decisions/0020-version-with-conventional-commits-and-release-please.md). Read this before changing a workflow or cutting a release.

## Flow

```
develop ─► PR "feat: …" ─► CI jobs + PR-title check ─► squash merge to main
                                                          │
                       release-please opens or updates "chore(main): release X.Y.Z"
                                                          │  merge when a milestone is done
                                     tag vX.Y.Z + GitHub Release + CHANGELOG.md entry
```

`develop` is a permanent integration branch ([0022](../decisions/0022-keep-a-long-lived-develop-branch.md)). After every merge into `main`, including release PRs, merge `main` back into it so the next PR shows only new work:

```
git checkout develop && git pull && git merge origin/main && git push
```

## CI jobs (`ci.yml`, on every pull request and push to `main`)

| Job | Runs | Catches |
|---|---|---|
| `lint` | `ruff check`, `ruff format --check`, `uv lock --check` | Bug-prone patterns, unused code, unformatted code, `pyproject.toml` changed without the lock |
| `types` | `mypy --strict src tests`, `lint-imports` | Type errors; a layer importing what it must not ([Code architecture](../system-design/code-architecture.md)) |
| `test` | `pytest -m "not nlp" --cov` | Logic regressions, coverage below 85 % |
| `nlp` | `uv sync --extra model`, then `make test-nlp`; the model wheel is kept in the job's own uv cache entry (`cache-suffix: nlp`) | 0011 key regressions and golden-corpus precision or recall below the baseline ([NVV extraction](../system-design/nvv-extraction.md)) |
| `docs` | `python tools/docs/validate_docs.py --docs-root docs` | Broken frontmatter, names or a stale docs index |

Plus `pr-title.yml`: the PR title must be a Conventional Commit, because it becomes the squash commit that release-please reads.

Workflow conventions:

- `astral-sh/setup-uv` with caching, and `uv sync --locked`, so CI uses exactly the lock file.
- Python version from `.python-version`; one version only (single user, R1).
- `permissions: contents: read` by default; only the release workflow can write.
- `concurrency` cancels superseded runs on the same branch.
- Third-party actions pinned to a commit SHA; Dependabot keeps them current.
- `make check` runs the same commands locally.

## Repository settings

Set once by hand in GitHub:

- Branch protection on `main`: pull request required, all CI jobs and the PR-title check required, branch up to date before merge, no force pushes.
- Branch protection on `develop`: no deletion, no force pushes, admins included; no PR or checks required. Protection also stops the automatic deletion below.
- Squash merge only; default squash message is the PR title; delete branches after merge (except protected ones such as `develop`).
- Secret scanning and push protection on (free for public repositories), as a backstop for R3.
- Dependabot alerts on. `dependabot.yml` updates `github-actions` and `uv` weekly, grouped into one PR each.

## Deliberately left out

| Not added | Why |
|---|---|
| Python version matrix | One user on one Python; add a version when the owner upgrades. |
| Publishing to PyPI | Sharing is a non-goal; install from a git tag. |
| Release wheels or binaries | `uv tool install git+…@vX.Y.Z` is enough. |
| Separate security scanners (CodeQL, gitleaks, bandit) | Push protection, Dependabot and ruff cover the real risks of a local CLI; add one if a need shows up. |
| Tests against real Anki or the real API in CI | Needs secrets and a desktop app (R28); covered by the manual release checklist. |

## Commit and PR title convention

Squash merge makes the PR title the only commit message that matters. Format: `type(optional-scope): summary`, imperative, lowercase type.

| Type | Use for | In CHANGELOG | Version bump |
|---|---|---|---|
| `feat` | New user-visible behaviour | Features | minor |
| `fix` | Bug fix | Bug Fixes | patch |
| `perf` | Faster, same behaviour | Performance | patch |
| `refactor`, `test`, `docs`, `ci`, `build`, `chore` | Everything else | hidden | none |

A breaking change adds `!` (`feat!: …`) or a `BREAKING CHANGE:` footer. For this project, breaking means:

- a CLI command, flag or config key removed or renamed;
- a chunk key format change (0011), since every note's key must be migrated;
- a new note type version (`-v2`), since existing notes must be migrated;
- a database migration that cannot be applied automatically.

Before 1.0.0, a breaking change bumps the minor version instead of the major (`bump-minor-pre-major`).

## Releases with release-please

- `release-please.yml` runs on every push to `main`. It keeps one open release PR that bumps the version in `pyproject.toml` and adds a `CHANGELOG.md` section built from the squash commits since the last tag.
- Merging the release PR creates the `vX.Y.Z` tag and a GitHub Release with the same notes. `include-component-in-tag: false` keeps the tag plain; release-please's default would be `learn-german-vX.Y.Z`. 0.1.0 was released under that default name, so `v0.1.0` was added by hand on the same commit.
- Cadence: merge the release PR when any milestone's done-when check passes, or earlier for an urgent fix. Versions count up as features land and do not map to milestones ([0023](../decisions/0023-release-as-features-land.md)).
- 1.0.0 is forced with a `Release-As: 1.0.0` footer at M8; see [Forcing 1.0.0](#forcing-100).
- Before merging a release PR that changes `adapters/`, the prompt, the note types or the CLI, and always for 1.0.0, run the manual [Release checklist](release-checklist.md).

### Release notes for several milestones at once

`develop` reaches `main` as one squash commit, so its title alone would give one changelog line. When several milestones are on `develop` since the last release, the `develop` → `main` PR body lists one Conventional Commit per milestone between `BEGIN_COMMIT_OVERRIDE` and `END_COMMIT_OVERRIDE` ([0041](../decisions/0041-run-the-remaining-milestones-sequentially.md)). release-please reads that block instead of the squash commit's message, so the block must be in the PR body before the PR is merged. Separate the lines with blank lines: release-please splits the block into commits at a blank line followed by a commit type. Take the lines from the merge commits on `develop`: `git log --first-parent --format=%s <last release tag>..develop`, skipping `docs:` and `chore:` lines that need no changelog entry.

### Forcing 1.0.0

release-please uses the version in a `Release-As: x.y.z` footer of any commit it reads instead of computing one. Because the override block replaces the squash commit's message, the footer goes **inside the block**, as the last paragraph, after a blank line. A `Release-As` line in the squash commit body or outside the block is ignored when a block is present. Do not put the footer in any other commit, and do not edit versions by hand: release-please owns `pyproject.toml`, `.release-please-manifest.json` and `CHANGELOG.md`.

Steps for the owner, after M8 is merged into `develop` and the [release checklist](release-checklist.md) and the [card quality measurement](../research/card-quality-v1.md) are done:

1. Push `develop`, then open the PR `develop` → `main` with the title `feat: release v1 (M2 to M8)` and this body, exactly:

   ```text
   Milestones M2 to M8 since 0.2.0. Release checklist: <link or ticked copy>.

   BEGIN_COMMIT_OVERRIDE
   feat: add NVV extractor (M2)

   feat: add sources with add, status and reextract (M3)

   feat: add chunk selection (M4)

   feat: add card generation (M5)

   feat: add Anki export through AnkiConnect (M6)

   feat: add sync to push generated notes to Anki (M7)

   feat: harden v1 with README, verbose logging and release checklist (M8)

   Release-As: 1.0.0
   END_COMMIT_OVERRIDE
   ```

2. When the checks pass, squash-merge it. release-please then opens `chore(main): release 1.0.0`, with seven Features entries in `CHANGELOG.md`.
3. Check that the release PR says 1.0.0 and that its lock-refresh commit passed, then merge it. That creates the tag `v1.0.0` and the GitHub Release.
4. Merge `main` back into `develop` ([0022](../decisions/0022-keep-a-long-lived-develop-branch.md)) and repeat step 1 of the release checklist with `@v1.0.0`.

If release-please proposes another version, edit the merged PR's body to fix the block; release-please rereads it on its next run, which a push to `main` (or re-running the workflow) starts. As a last resort, `"release-as": "1.0.0"` in `release-please-config.json` forces the version too; remove it again after the release.

Base config (`release-please-config.json`):

```json
{
  "packages": {
    ".": {
      "release-type": "python",
      "package-name": "learn-german",
      "include-component-in-tag": false,
      "bump-minor-pre-major": true,
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance" },
        { "type": "refactor", "section": "Refactoring", "hidden": true },
        { "type": "docs", "section": "Documentation", "hidden": true },
        { "type": "test", "section": "Tests", "hidden": true },
        { "type": "ci", "section": "CI", "hidden": true },
        { "type": "build", "section": "Build", "hidden": true },
        { "type": "chore", "section": "Chores", "hidden": true }
      ]
    }
  }
}
```

### Two pitfalls and how M0 solves them

1. **`uv.lock` holds the project's own version.** A release PR that bumps only `pyproject.toml` fails `uv lock --check`. Solved with a step in `release-please.yml`: whenever release-please creates or updates its PR, the workflow checks out the release branch, runs `uv lock` and pushes the result if it changed. This was chosen over a release-please `extra-files` TOML updater because the jsonpath filter over `uv.lock`'s `[[package]]` array depends on release-please's TOML parser internals, while `uv lock` is always right. M0 is done only when the release PR passes the lock check.
2. **PRs opened with the default `GITHUB_TOKEN` do not trigger other workflows.** The release PR's required checks would never run, so it could not be merged. release-please and the lock-refresh push both use a fine-grained token, `RELEASE_PLEASE_TOKEN`, limited to this repository, with contents and pull-request write access. It is the only secret in the repository and only the release workflow uses it; tests still need none (R28).

### One-time setup for releases

1. Create a fine-grained personal access token: repository access *only this repository*; permissions *Contents: read and write*, *Pull requests: read and write*.
2. Store it as the Actions secret `RELEASE_PLEASE_TOKEN`.
3. Apply the [repository settings](#repository-settings) and mark `lint`, `types`, `test`, `docs` and `conventional-commit` as required checks (add `nlp` in M2).

## Installing a release

```bash
uv tool install 'learn-german[model] @ git+https://github.com/<owner>/learn-german@v1.0.0'
```

Upgrade by installing a newer tag with `--force`. The `model` extra brings the spaCy model; without it `add` and `reextract` stop with an error. The [README](../../README.md) is the user-facing version of these steps.

## Related

- [Release checklist](release-checklist.md)
- [Coding conventions](coding-conventions.md)
- [Testing strategy](testing-strategy.md)
- [Roadmap](../product/roadmap.md)

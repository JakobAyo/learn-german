---
title: Release checklist
summary: Manual end-to-end check against real Anki and the real Claude API: fresh install, add, dry run, three notes, no duplicates, rendering, failure paths.
status: active
updated: 2026-11-27
---

# Release checklist

## Purpose

CI never talks to a real Anki or the real Claude API ([0019](../decisions/0019-gate-main-with-ci-checks.md), R28). This checklist is the manual test layer of [Testing strategy](testing-strategy.md): it installs the tool the way a user does and runs the whole `add` → `status` → `sync` workflow against both. Run it before merging the release PR of 1.0.0, and before any later release that changes `adapters/`, the prompt, the note types or the CLI. It costs a few cents of API usage.

Record the outcome in the release PR as a ticked copy of the checklist below. A failed step blocks the release until it is fixed or explained.

## Before you start

- **Anki:** create a throwaway profile (File, Switch Profile, Add, for example `learn-german-release`) and open it. Never run the checklist against your real collection. AnkiConnect is shared across profiles, so nothing else needs setting up.
- **A clean state:** use a new shell whose config and data directories are empty, so neither your real database nor your real `config.toml` is touched, and run it from an empty directory so no `.env` is read:

  ```bash
  export XDG_CONFIG_HOME="$(mktemp -d)" XDG_DATA_HOME="$(mktemp -d)"
  cd "$(mktemp -d)"
  unset ANTHROPIC_API_KEY
  ```

- **What to install:** before the release there is no tag yet. Until the develop → main PR is merged, the changes to check exist only on `develop`, so install from `develop`; `main` still holds the previous release. Once that PR is merged, install from `main`, which holds everything the release PR will tag. After the tag exists, repeat step 1 with the tag to check the version. `--version` prints the previous version until the release PR bumps it.
- **A small test text.** Save this hand-written text as `release-check.txt` in the working directory. It holds three clear Nomen-Verb-Verbindungen, so the sync steps have a known size. Do not commit it, and do not use a real article for it.

  ```text
  Der Stadtrat hat am Dienstag nach einer langen Debatte endlich eine Entscheidung über die neue Brücke getroffen.

  Die Stadt stellt dem Sportverein ab dem kommenden Frühjahr zwei renovierte Hallen in der Altstadt zur Verfügung.

  Die Opposition übte in der Sitzung am Mittwochabend scharfe Kritik an den hohen Kosten des Projekts.
  ```

- **Two or three German news URLs** from a site whose `robots.txt` allows fetching, and one URL you know is behind a paywall.

## Checklist

### 1. Fresh install

- [ ] `uv tool uninstall learn-german` (ignore "not installed").
- [ ] `uv tool install 'learn-german[model] @ git+https://github.com/JakobAyo/learn-german@develop'` (or `@main` once the develop → main PR is merged, `@vX.Y.Z` once tagged). It installs without errors; the model wheel is part of it.
- [ ] `learn-german --version` prints the expected version (after tagging: `X.Y.Z`).
- [ ] `learn-german --help` lists `add`, `status`, `reextract`, `sync` and the options `--verbose`, `--version`.
- [ ] Every command in the [README](../../README.md) still matches `learn-german <command> --help`.

### 2. Failure paths before configuration

- [ ] `learn-german sync --dry-run` exits 2 with "ANTHROPIC_API_KEY is not set" and says where to create one.

### 3. Add and status

- [ ] `learn-german add release-check.txt` prints `added` with 3 chunks, 3 new, and exits 0.
- [ ] `learn-german add release-check.txt` again prints `skipped ... already added`.
- [ ] `learn-german status` lists 1 source and 3 pending chunks: `entscheidung|treffen`, `verfügung|zu|stellen`, `kritik|üben`. If the extractor finds a different number N, write it down and use N wherever 3 appears below.
- [ ] `export ANTHROPIC_API_KEY=sk-ant-invalid`, then `learn-german sync --dry-run --cap 1` exits 2 with "The Claude API rejected the API key. Check ANTHROPIC_API_KEY.", and `sk-ant-invalid` appears nowhere in the output.
- [ ] `export ANTHROPIC_API_KEY=<your real key>`.

### 4. Anki closed

- [ ] With Anki closed, `learn-german -v sync --cap 3` exits 2 with "Cannot reach AnkiConnect ... Start Anki", and the log shows no "Calling Claude" line: nothing was paid for.
- [ ] With Anki still closed, `learn-german sync --dry-run --cap 3` prints the warning that it cannot ask Anki, then previews the notes, and exits 0.

### 5. Dry run

- [ ] Open Anki on the throwaway profile.
- [ ] `learn-german sync --dry-run --cap 3` prints `Dry run run-...: 3 chunks selected`, a `would add` block with the transformation note's fields per chunk, and "3 notes would be added". Exit 0.
- [ ] Anki is unchanged: no `learn-german::chunks` deck, no `learn-german-*` note types.
- [ ] Read the previewed fields. Each chunk's citation form, meaning, shortened sentence and verbal rewrite make sense; note anything wrong for the [quality measurement](../research/card-quality-v1.md).

### 6. Sync: three notes

- [ ] `learn-german -v sync --cap 3` prints `Run run-...: 3 chunks done, 3 notes added to Anki`, exits 0, and its log shows three "LLM cache hit" lines and no "Calling Claude" line: the dry run's answers were reused.
- [ ] In Anki, Browse shows exactly 3 notes in `learn-german::chunks`, all of `learn-german-transformation-v1`, each tagged `learn-german`, `provider::anthropic`, `model::claude-opus-5-5` and the run's `run::` tag.
- [ ] `learn-german status` says no chunks are pending.

### 7. A repeated sync adds nothing

- [ ] `learn-german sync` prints "Nothing to sync", adds nothing and exits 0.
- [ ] Anki still has 3 notes.
- [ ] With a second, empty database, Anki alone prevents duplicates ([0033](../decisions/0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)): `LEARN_GERMAN_DATABASE_PATH="$(mktemp -d)/fresh.db" sh -c 'learn-german add release-check.txt && learn-german sync --cap 3'` prints "Nothing to sync" and Anki still has 3 notes.

### 8. Card rendering

- [ ] In Anki, preview the card of one chunk, in light and in night mode. Check front, back, the bold chunk, the italic meaning and that `ChunkKey` shows on neither side, as described in step 3 of the [AnkiConnect smoke test](../integrations/ankiconnect.md#manual-smoke-test). If this release changed `adapters/anki/` or the note types, run that whole smoke test too.
- [ ] Study one card in the throwaway profile: the answer is a sentence you could produce from the front.

### 9. Real articles and fetch failures

- [ ] `learn-german add <news URL 1> <news URL 2>` prints `added` with a title and some chunks for each, exit 0.
- [ ] `learn-german add <paywalled URL>` prints `failed` with advice to save the text as a `.txt` file, and exits 1.
- [ ] `learn-german -v add --force <news URL 1>` logs the robots.txt read, the GET, the word count and the extractor's counts, and prints `refreshed`.
- [ ] `learn-german -v sync --dry-run --cap 1 2>&1 | grep -c 'sk-ant'` prints `0`.

### 10. Anki failure during a run

- [ ] With the chunks from step 9 pending, open a dialog in Anki (for example Tools, Preferences) and run `learn-german sync --cap 1`. If the dialog blocks AnkiConnect, the command exits 2 after 30 seconds with "did not answer ... in time. Close any open dialog"; if AnkiConnect keeps answering, the note is added normally. Either outcome passes; a hang or a traceback fails. Close the dialog.

### 11. Clean up

- [ ] `unset ANTHROPIC_API_KEY`; delete the temporary directories.
- [ ] In Anki, delete the throwaway profile and switch back to your own.

## For 1.0.0 only

- [ ] Run `tools/eval/run_eval.py` if the prompt or model changed since the last run, and read its output ([Claude API](../integrations/claude-api.md#manual-evaluation)).
- [ ] Complete the [card quality measurement](../research/card-quality-v1.md) and act on its outcome.
- [ ] Open the develop → main PR with the `BEGIN_COMMIT_OVERRIDE` block and the `Release-As: 1.0.0` footer described in [CI and releases](ci-and-releases.md#forcing-100).

## Related

- [Testing strategy](testing-strategy.md)
- [CI and releases](ci-and-releases.md)
- [AnkiConnect](../integrations/ankiconnect.md)
- [Claude API](../integrations/claude-api.md)
- [README](../../README.md)

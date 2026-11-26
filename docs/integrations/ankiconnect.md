---
title: AnkiConnect
summary: How the Anki adapter talks to the running Anki app through AnkiConnect: setup, settings, actions used, failure modes, tests and the manual smoke test.
status: active
updated: 2026-11-26
---

# AnkiConnect

## Purpose

Describes the export side of `sync`: how notes reach the running Anki desktop app ([0003](../decisions/0003-push-notes-live-through-ankiconnect.md)), what the tool asks Anki for, and what happens when Anki is not there. Read this before changing `adapters/anki/`, the note type templates or the deck setting. What the cards contain is in [Note types](../learning-design/note-types.md).

## Setup

1. Install Anki desktop and the AnkiConnect add-on (Tools, Add-ons, Get Add-ons, code `2055492159`), then restart Anki.
2. Leave AnkiConnect's configuration at its defaults. It listens on `127.0.0.1:8765`. Its `apiKey` must stay `null`, because the tool sends no key ([0040](../decisions/0040-add-notes-one-call-each-and-split-ankiconnect-errors.md)).
3. Keep Anki open, with no dialog showing, while `sync` runs. `sync --dry-run` does not need Anki.

## Settings

| Setting | Default | Where |
|---|---|---|
| Deck | `learn-german::chunks` | `deck` setting, `LEARN_GERMAN_DECK` |
| AnkiConnect URL | `http://127.0.0.1:8765` | `anki_connect_url` setting, `LEARN_GERMAN_ANKI_CONNECT_URL` |

See [Configuration](../development/configuration.md). The request timeout (30 s) is a constructor default of `AnkiConnectClient`, not a setting.

## Modules

| Module | Role |
|---|---|
| `adapters/anki/client.py` | `AnkiConnectClient`: the JSON envelope, the `error` field, transport failures, the version check. |
| `adapters/anki/gateway.py` | `AnkiConnectGateway`, which implements `ports.AnkiGateway`. |
| `adapters/anki/note_types.py` | `NoteTypeSpec`, `TRANSFORMATION_V1`, `TRANSLATION_V1` and `NOTE_TYPES`. |
| `adapters/anki/templates/` | Card fronts and backs (`*_front.html`, `*_back.html`) and `style_v1.css`. |
| `adapters/anki/errors.py` | `AnkiActionError` (fatal). |
| `application/notes/` | `NoteBuilder` and `run_tags`: card content to the two `NoteDraft`s. |

Bootstrap wires `AnkiConnectGateway(AnkiConnectClient(settings.anki_connect_url), deck=settings.deck)` in M7.

## Protocol

Every request is an HTTP `POST` of `{"action": …, "version": 6, "params": {…}}` to the URL; every answer is `{"result": …, "error": null | "message"}`.

| Action | Sent by | Params |
|---|---|---|
| `version` | `ensure_setup` | none; the answer must be 6 or more |
| `deckNames`, `createDeck` | `ensure_setup` | `deck`; created only if missing |
| `modelNames` | `ensure_setup` | none |
| `modelFieldNames` | `ensure_setup`, for each note type that exists | `modelName` |
| `createModel` | `ensure_setup`, for each note type that is missing | `modelName`, `inOrderFields`, `css`, `isCloze: false`, `cardTemplates` |
| `findNotes` | `existing_keys` | `query`: `"note:<note type name>"`, no deck term ([0039](../decisions/0039-read-existing-keys-per-note-type-across-the-collection.md)) |
| `notesInfo` | `existing_keys`, only if `findNotes` found notes | `notes`: the IDs; the `ChunkKey` field of each is read |
| `addNote` | `add_notes`, once per draft | `deckName`, `modelName`, HTML-escaped `fields`, `tags`, `options: {allowDuplicate: false, duplicateScope: "collection"}` |

`ensure_setup` never changes an existing note type: matching fields leave it as it is, including any restyling done in Anki; other fields stop the run ([0038](../decisions/0038-create-missing-note-types-and-check-only-their-fields.md)).

## Failures

| Situation | Error | Effect in `sync` |
|---|---|---|
| Anki closed, wrong URL, connection refused | `AnkiUnavailableError` | Fatal: stop, exit 2. Message says to start Anki with AnkiConnect. |
| Anki busy with a dialog for 30 s | `AnkiUnavailableError` | Fatal. Message says to close the dialog. |
| Something else answers at the URL (not JSON, not the envelope, HTTP error) | `AnkiUnavailableError` | Fatal. |
| AnkiConnect older than version 6 | `AnkiUnavailableError` | Fatal. Message says to update the add-on. |
| AnkiConnect has an API key set | `AnkiActionError` on `version` | Fatal. |
| Note type exists with other fields | `NoteTypeMismatchError` | Fatal, before any note is added. |
| Setup or search action answers with an error or a wrong shape | `AnkiActionError` | Fatal. |
| `addNote` rejected (duplicate, empty first field) | `PushError` | Item: the chunk stays pending with its error; notes added before it stay, and the next sync adds only what is missing. |

## Testing

- `tests/integration/anki/test_client.py`: the client against `httpx2.MockTransport`: request shape, the `error` field, connection refused, timeouts, answers that are not AnkiConnect's, the version check.
- `tests/integration/anki/mock_ankiconnect.py`: `MockAnkiConnect`, an in-memory collection that answers the actions above as AnkiConnect 6 does, including Anki's duplicate check.
- `tests/integration/anki/test_gateway.py`: the requests the real gateway sends and how it fails.
- `tests/contract/test_anki_gateway.py`: one suite run against `FakeAnkiGateway` and against `AnkiConnectGateway` over `MockAnkiConnect`.
- `tests/unit/notes/`: `NoteBuilder`, tags, the frozen v1 field lists, and the cards rendered against golden files in `tests/data/anki/`.

No test talks to a real Anki.

## Manual smoke test

Run before a release that touches `adapters/anki/` or the note types, against a throwaway profile, never the real collection. Until `sync` exists (M7) it drives the gateway from Python.

1. In Anki, File, Switch Profile, Add: create `learn-german-smoke` and open it. AnkiConnect is shared across profiles.
2. From the repository, run `uv run python`, then:

   ```python
   from learn_german.adapters.anki import AnkiConnectClient, AnkiConnectGateway
   from learn_german.application.notes import NoteBuilder
   from learn_german.domain.models import (
       CardContent,
       CardRequest,
       ChunkKey,
       ChunkKind,
       NoteKind,
       RunId,
   )

   gateway = AnkiConnectGateway(
       AnkiConnectClient("http://127.0.0.1:8765"), deck="learn-german::chunks"
   )
   gateway.ensure_setup()
   gateway.ensure_setup()  # idempotent: no error, nothing new in Anki
   key = ChunkKey("entscheidung|treffen")
   request = CardRequest(key, ChunkKind.NVV, "Der Stadtrat hat eine Entscheidung getroffen.", "", "en")
   content = CardContent(
       citation_form="eine Entscheidung treffen",
       shortened_sentence="Der Stadtrat hat am Montag eine Entscheidung über die Brücke getroffen.",
       verbal_rewrite="Der Stadtrat hat am Montag über die Brücke entschieden.",
       translation="The city council made a decision about the bridge on Monday.",
       meaning="eine Entscheidung treffen = entscheiden, sich festlegen & <festlegen>",
   )
   builder = NoteBuilder.for_run(
       provider="anthropic", model="claude-opus-5-5", run_id=RunId("run-20261126-1200")
   )
   gateway.add_notes(builder.build(request, content))
   print({kind: gateway.existing_keys(kind) for kind in NoteKind})  # the key under both kinds
   gateway.add_notes(builder.build(request, content))  # raises PushError: duplicate
   ```

3. In Anki, check:
   - Tools, Manage Note Types lists `learn-german-transformation-v1` (fields `ChunkKey, Chunk, Meaning, Answer, Prompt`) and `learn-german-translation-v1` (the same plus `HintLanguage`), each with one card type.
   - The deck `learn-german::chunks` exists and Browse shows exactly two notes, tagged `learn-german`, `provider::anthropic`, `model::claude-opus-5-5` and `run::run-20261126-1200`.
   - Preview each card. Transformation front: "Rewrite in nominal style, using an NVV:" and the verbal sentence; back: front, a line, the answer, the chunk in bold, the meaning in italics. Translation front: the English prompt and "Use: **eine Entscheidung treffen**"; back: front, a line, the answer, the meaning. `ChunkKey` is on neither side; the meaning shows `& <festlegen>` literally. Check light and night mode.
4. Run `gateway.ensure_setup()` again and confirm in Anki that the deck and note types are unchanged.
5. Rename a field of one note type in Anki, run `gateway.ensure_setup()`: it raises `NoteTypeMismatchError` naming both field lists. Rename it back.
6. Close Anki and run `gateway.ensure_setup()`: it raises `AnkiUnavailableError` saying to start Anki.
7. Delete the `learn-german-smoke` profile.

## Related

- [Note types](../learning-design/note-types.md)
- [Pipeline](../system-design/pipeline.md)
- [Code architecture](../system-design/code-architecture.md)

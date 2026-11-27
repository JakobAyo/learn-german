---
title: Add notes one call each, escape field values, and split AnkiConnect errors into fatal and item
summary: One addNote call per note so a rejection is attributable, field values HTML-escaped, unreachable or failing setup is fatal, a rejected note is a PushError.
status: active
updated: 2026-11-26
---

# Add notes one call each, escape field values, and split AnkiConnect errors into fatal and item

## Context

The `AnkiGateway` port says `add_notes` raises an `ItemError` if Anki rejects a note and a `FatalError` if Anki is unreachable ([0014](0014-keep-progress-when-a-run-fails-partway.md)). AnkiConnect's batch action `addNotes` reports partial failures differently across versions: older versions put `null` into the result list, newer ones answer with one error that lists every failure without saying which notes were added. Anki fields hold HTML, while the LLM writes plain text that can contain `<` or `&`. AnkiConnect also drops a field it does not know without an error.

## Decision

- **One `addNote` call per draft**, in order. A rejected note raises `PushError` with the note kind, the chunk key and Anki's reason. Notes before it stay in Anki; the drafts after it are not sent. `sync` records the chunk's error, and the next sync's Anki check ([0033](0033-count-a-note-as-present-if-the-local-record-or-anki-has-it.md)) sees the note that was added and creates only the one still missing.
- **Field values are escaped** with `html.escape(value, quote=False)` before they are sent, so they show as written. `ChunkKey` values are unescaped when read back.
- A draft whose field names are not its note type's raises `ValueError` before any request. It can only be a bug, since `NoteBuilder` and the specs are tested to agree.
- **Error mapping** of `AnkiConnectClient` and `AnkiConnectGateway`:

  | What happens | Raised as | Why |
  |---|---|---|
  | Connection refused, other transport error, timeout (30 s) | `AnkiUnavailableError` (fatal) | Anki is closed or busy; every further call fails too |
  | Non-200 status, no JSON, no `result`/`error` envelope | `AnkiUnavailableError` | Something other than AnkiConnect answers at the URL |
  | AnkiConnect older than API version 6 | `AnkiUnavailableError` | The envelope and actions this tool uses need version 6 |
  | `error` field on a setup or search action, or a result of the wrong shape | `AnkiActionError` (fatal, adapter subclass) | A failing setup or search fails the same way for every chunk |
  | `error` field on `addNote` | `PushError` (item) | Only this note is affected, for example a duplicate |

- Requests use API version 6 and send no `key`: AnkiConnect's optional API key is not supported in v1, so it must stay unset.

## Alternatives considered

- **One `addNotes` call per chunk:** one request fewer per chunk, but which notes were added after a failure depends on the AnkiConnect version.
- **Checking first with `canAddNotesWithErrorDetail`:** an extra call per chunk, and the add can still fail afterwards.
- **No escaping:** an LLM answer with `<` or `&` could break or hide part of the card.
- **Every AnkiConnect error as an item error:** a missing deck or note type would fail each chunk on its own, after its LLM call was paid for.

## Consequences

- Two local HTTP calls per chunk instead of one, which is negligible next to the LLM call.
- A crash or rejection between a chunk's two notes leaves it partial in Anki; the next sync completes it.
- An AnkiConnect with an API key set fails at the version check with AnkiConnect's own message, which is fatal.

## Related

- [AnkiConnect](../integrations/ankiconnect.md)
- [0003 Push notes live through AnkiConnect](0003-push-notes-live-through-ankiconnect.md)

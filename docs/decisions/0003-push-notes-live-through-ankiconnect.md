---
title: Push notes live through AnkiConnect into a tool-owned deck
summary: Notes go into the running Anki desktop app through AnkiConnect, into a deck and versioned note types the tool owns, instead of .apkg files.
status: active
updated: 2026-11-24
---

# Push notes live through AnkiConnect into a tool-owned deck

## Context

Cards must reach Anki without manual steps. Deduplication needs to know which chunks are already in Anki, and a later known-item filter may need to read the collection.

## Decision

- Use the AnkiConnect add-on to add notes to the running Anki desktop app.
- The tool creates and owns one deck and its own note types. It never modifies notes in other decks.
- Note types carry a version. Changing their fields is a migration: the tool updates existing notes instead of creating a parallel type.

## Alternatives considered

- `.apkg` export with `genanki`: rejected. It cannot read the collection for deduplication, cannot update notes, and needs a manual import.
- Both, with `.apkg` as a fallback: rejected. It means two export paths to maintain for little gain.
- Mapping onto the owner's existing note types: rejected. It couples the tool to a personal setup that a public repo cannot know.

## Consequences

- Anki desktop with AnkiConnect must be running during a push. The tool must fail with a clear message when it is not; `--dry-run` works without it.
- The deck name and AnkiConnect URL are config, not code.
- Note type field design must be settled carefully before v1, since changes later need migrations.

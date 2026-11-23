---
title: Decisions
summary: Numbered decision records (ADRs). Why the project is the way it is, one decision per file.
---

# Decisions

Every non-trivial choice that shaped this project gets one record here. Records are append-only. A changed decision gets a new record that supersedes the old one; the old record stays, with its status set to `superseded`.

## What belongs here

- Architecture and technology choices, and the alternatives that were rejected.
- Process and convention decisions (branching model, review rules, release cadence).
- Anything a future reader might otherwise undo because they do not know why it was done.

## What does not belong here

- Descriptions of how the system works today. Those go in the concern folder they belong to, and the record links to them.
- Task lists, meeting notes, or status updates.

## How to add a record

Use the helper, which picks the next number and writes valid frontmatter:

```bash
python3 ~/.claude/skills/docs-architect/scripts/new_doc.py --docs-root docs --adr --title "Use PostgreSQL for primary storage"
```

Or copy this template into `NNNN-short-title.md` by hand:

```markdown
---
title: Short imperative title
summary: One line stating the decision and its main reason.
status: active
updated: YYYY-MM-DD
---

# Short imperative title

## Context

What situation or problem forced a choice. Constraints that mattered.

## Decision

What was decided, stated plainly.

## Alternatives considered

- Option A: why it was rejected.
- Option B: why it was rejected.

## Consequences

What becomes easier, what becomes harder, what must be revisited later.
```

Status meanings for records: `draft` = proposed and not yet agreed, `active` = accepted and in force, `deprecated` = no longer applies and nothing replaced it, `superseded` = replaced by a newer record (name it in the body).

<!-- docs-index:start -->

## Contents

- [Adopt a concern-based documentation structure](0001-adopt-documentation-structure.md) — Documentation is split into one folder per concern, each indexed by a CLAUDE.md, with decisions recorded as numbered records.

<!-- docs-index:end -->

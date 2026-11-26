---
title: Card quality of v1
summary: Method, rubric and empty results table for measuring how often v1's generated cards are wrong, and how the error rate decides on 0005.
status: draft
updated: 2026-11-26
---

# Card quality of v1

## Purpose

[Requirements](../product/requirements.md#open-questions) leaves one question open: with no review step and no self-check pass, how often is the generated content wrong? [0005](../decisions/0005-push-cards-automatically-with-tagging-and-dry-run.md) accepts that wrong cards reach the deck and says to measure the error rate once v1 runs. This document is the measurement for v1 (prompt `card-v1`, model `claude-opus-5-5`, effort `medium`). It is a draft until the owner has run it and filled in the results; then its status becomes `active` and its conclusion goes into a decision record.

Nothing here has been measured yet. The results table is empty on purpose.

## Method

1. **Sources.** Pick five real German articles of the kind the tool is meant for: news or features at B2 to C1 level, from at least three different sites or topics (politics, economy, science, culture, local news). Add them with `learn-german add`; use the `.txt` fallback for any that fail. Do not commit the articles or their sentences ([0002](../decisions/0002-build-a-single-user-python-cli-in-a-public-repo.md)).
2. **Sample.** Generate ten chunks with a dry run and keep its output outside the repository:

   ```bash
   learn-german sync --dry-run --cap 10 > ~/card-quality-v1.txt
   ```

   Ten chunks give 20 notes, the 20 cards to grade. The sample is the top ten by the normal ranking ([0034](../decisions/0034-rank-partial-chunks-first-then-by-occurrences.md)), which is what a real `sync` would add. Note the run ID from the first line. The answers are cached, so a later real `sync` adds exactly these notes at no further cost.
3. **Extraction check.** Before grading the cards, check that each chunk key is a real Nomen-Verb-Verbindung in its source sentence. A wrong key is an extraction error, not a card error; count it separately, because it points at the extractor ([0031](../decisions/0031-guard-extraction-with-a-golden-corpus-baseline.md)), not at 0005.
4. **Grading.** Grade every field of every note with the rubric below, from the dry-run file, without looking anything up first; then check doubtful cases in a dictionary (Duden, DWDS). Grade a field as an error only if it would teach something wrong or make the card unanswerable; style preferences are not errors.
5. **Record** one row per note in the results table, with the chunk key only (no sentences), and the error count per field.

Total cost: ten Claude calls, a few cents.

## Rubric

A note is **wrong** if any of its fields has an error. Fields shared by both note types are graded once per note, so a bad `Chunk` counts against both notes of its chunk.

| Field | Note types | Counts as an error |
|---|---|---|
| `Chunk` (citation form) | both | Not the form a dictionary lists (wrong article or preposition, e.g. *in die Kritik üben*); a different chunk than the key; not an NVV at all. |
| `Meaning` | both | Wrong or misleading meaning; explains a different sense than the one in the sentence; not German. |
| `Answer` (shortened sentence) | both | Ungrammatical German; meaning changed from the source sentence; chunk missing or changed; not one self-contained sentence. Shorter than 10 or longer than 20 words is not an error by itself (the checks of [0036](../decisions/0036-check-card-content-then-cache-it-in-its-own-transaction.md) already bound it). |
| `Prompt` (verbal rewrite) | transformation | Ungrammatical; still uses the chunk or its noun; meaning differs from `Answer`; other words changed so much that `Answer` is not the natural nominal rewrite of it. |
| `Prompt` (translation) | translation | Not in the hint language; wrong or unnatural translation of `Answer`; a translation from which the learner could not reasonably arrive at `Answer` with the given chunk. |

Severity, for the notes column: **misleading** (would teach a mistake: wrong German, wrong meaning) or **unusable** (the card cannot be answered as intended, but teaches nothing false).

## Results

To be filled in by the owner.

- Date:
- Version (`learn-german --version`):
- Run ID of the dry run:
- Sources: 5 articles, sites or topics:
- Extraction errors (chunk keys that are not NVVs): __ of 10

| # | Chunk key | Note type | Chunk | Meaning | Answer | Prompt | Wrong? | Notes (severity, what was wrong) |
|---|---|---|---|---|---|---|---|---|
| 1 | | transformation | | | | | | |
| 2 | | translation | | | | | | |
| 3 | | transformation | | | | | | |
| 4 | | translation | | | | | | |
| 5 | | transformation | | | | | | |
| 6 | | translation | | | | | | |
| 7 | | transformation | | | | | | |
| 8 | | translation | | | | | | |
| 9 | | transformation | | | | | | |
| 10 | | translation | | | | | | |
| 11 | | transformation | | | | | | |
| 12 | | translation | | | | | | |
| 13 | | transformation | | | | | | |
| 14 | | translation | | | | | | |
| 15 | | transformation | | | | | | |
| 16 | | translation | | | | | | |
| 17 | | transformation | | | | | | |
| 18 | | translation | | | | | | |
| 19 | | transformation | | | | | | |
| 20 | | translation | | | | | | |

Mark each field `ok` or `error`. Then:

- Wrong notes: __ of 20 (__ %), of which misleading: __
- Errors per field: Chunk __, Meaning __, Answer __, Prompt (transformation) __, Prompt (translation) __

## How the result decides 0005

The error rate is wrong notes out of 20. Twenty notes give only a rough estimate, so the bands are wide and the misleading count weighs more than the total.

| Result | Meaning | Action |
|---|---|---|
| At most 2 wrong notes (≤ 10 %) and none misleading | Fixing cards while studying, as 0005 expects, costs little. | Keep 0005. Record the result in a decision record and set this document to `active`. |
| 3 or 4 wrong notes (15 to 20 %), or 1 or 2 misleading | Borderline. | Look at where the errors are. If one field or one note type holds most of them, fix the prompt (a new `PROMPT_VERSION`, [0035](../decisions/0035-version-the-card-prompt-as-a-template-with-a-pinned-hash.md)) or tighten a sanity check, then measure again on a fresh sample. Keep 0005 meanwhile. |
| 5 or more wrong notes (≥ 25 %), or 3 or more misleading | Too many wrong cards reach the deck. | Revisit 0005 in a new decision record that supersedes it: add an LLM self-check pass, or a review step before pushing, as 0005's alternatives describe. |

Extraction errors do not count towards these bands. If more than 2 of the 10 keys are not NVVs, open an extractor issue and extend the golden corpus with the failing cases.

The thresholds are a proposal for the owner to confirm when recording the result.

## Related

- [Requirements](../product/requirements.md)
- [0005 Push cards automatically](../decisions/0005-push-cards-automatically-with-tagging-and-dry-run.md)
- [Release checklist](../development/release-checklist.md)
- [Claude API](../integrations/claude-api.md)
- [Note types](../learning-design/note-types.md)

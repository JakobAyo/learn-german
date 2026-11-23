---
title: learn-german documentation
summary: Index of the documentation tree. Start here to find which folder holds what.
---

# learn-german documentation

A personal extraction tool that mines German source material (news articles, video subtitles) for chunks, chiefly Nomen-Verb-Verbindungen, and turns them into Anki cloze and sentence-transformation cards for spaced repetition. Its goal is to move a B2 learner towards C1 by widening the words they actually use and improving how they build sentences, rather than by adding passive word lists.

## How to use this index

- Each folder below covers exactly one concern. Read the folder's `CLAUDE.md` first; it states what belongs there and lists every file with a one-line summary.
- Open a file only when its summary matches what you need. Do not read the whole tree.
- Every decision that shaped this project is recorded in `decisions/` as a numbered record. Check there before changing an established approach.

## Conventions

- Folder and file names are kebab-case. Decision records are `NNNN-short-title.md`.
- Every document starts with frontmatter: `title`, `summary`, `status` (draft, active, deprecated, superseded), `updated` (YYYY-MM-DD).
- The index sections between the `docs-index` markers are generated. Edit the text outside them; regenerate the rest with `build_index.py`.

<!-- docs-index:start -->

## Index

### [data/](data/CLAUDE.md)

Input sources, frequency lists, known-words store and the extracted-item data model.

- (empty)

### [decisions/](decisions/CLAUDE.md)

Numbered decision records (ADRs). Why the project is the way it is, one decision per file.

- [Adopt a concern-based documentation structure](decisions/0001-adopt-documentation-structure.md) — Documentation is split into one folder per concern, each indexed by a CLAUDE.md, with decisions recorded as numbered records.

### [development/](development/CLAUDE.md)

Local setup, dependencies and NLP models, and how to run the extractor.

- (empty)

### [integrations/](integrations/CLAUDE.md)

External systems: Anki, translation, audio and any LLM; how each is called and fails.

- (empty)

### [learning-design/](learning-design/CLAUDE.md)

Card types, what each trains, Anki deck and note-type layout, review settings.

- (empty)

### [product/](product/CLAUDE.md)

Learning goals, scope, non-goals and roadmap of the extractor.

- [Learning goals](product/learning-goals.md) — B2 to C1 goal, the two core weaknesses (word finding, error-free sentences) and why Anki is the study channel.

### [research/](research/CLAUDE.md)

Experiments, evaluations and summaries of outside advice that inform decisions.

- [DeepSeek chat: chunks and sentence transformation](research/deepseek-chat-advice.md) — Summary and critique of the DeepSeek advice: mine Nomen-Verb-Verbindungen with spaCy, cloze and transformation cards via genanki.

### [system-design/](system-design/CLAUDE.md)

Extraction pipeline: ingest, NLP processing, filtering and ranking, card generation, export.

- (empty)

<!-- docs-index:end -->

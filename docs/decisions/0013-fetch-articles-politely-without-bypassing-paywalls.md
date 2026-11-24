---
title: Fetch articles politely, without bypassing paywalls
summary: The news-URL adapter fetches only the given URL, respects robots.txt and fails clearly on paywalls; a local .txt file is the fallback.
status: active
updated: 2026-11-24
---

# Fetch articles politely, without bypassing paywalls

## Context

The requirements left open how to handle paywalls, robots.txt and site terms. The repository is public, so its fetching behaviour should be something other people can run without trouble.

## Decision

- The news-URL adapter fetches only the URL the user gives. It never follows links or crawls.
- It sends an honest User-Agent naming the tool, and respects robots.txt.
- It never bypasses a paywall or login. If the page is blocked, paywalled, or yields too little text, the run reports this clearly and skips the source.
- The fallback is to save the article text to a `.txt` file and feed it through the local-file adapter.
- Fetched text is stored only in the local SQLite database (see [0007](0007-keep-local-state-in-sqlite.md)).

## Alternatives considered

- Fetch like a browser, ignoring robots.txt: rejected, because the public code should behave well on other people's machines too.
- Local files only in v1: rejected, because fetching by URL removes a manual step for most free articles.

## Consequences

- Some sites will not work. The error message must point to the `.txt` fallback.
- Main-text extraction uses a library built for article pages (see [0016](0016-use-standard-python-tooling.md)).

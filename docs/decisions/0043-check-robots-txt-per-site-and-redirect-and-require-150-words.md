---
title: Check robots.txt per site and redirect, and require 150 words of article text
summary: robots.txt is read like the standard library does and checked again per redirected site; at most five redirects; under 150 words counts as a paywall.
status: active
updated: 2026-11-26
---

# Check robots.txt per site and redirect, and require 150 words of article text

## Context

[0013](0013-fetch-articles-politely-without-bypassing-paywalls.md) asks the news adapter to fetch only the given URL, respect robots.txt, send an honest User-Agent and fail clearly on paywalls. It leaves open how robots.txt answers other than 200 are read, what to do with redirects, and how a paywall is recognised when the site answers 200 with a teaser.

## Decision

- **User-Agent** `learn-german/<version>`, with no URL or contact details. robots.txt rules are matched against `learn-german`, so a site can single the tool out, and `*` applies otherwise.
- **robots.txt is read before the first request to each site** and kept for the rest of the command. Its status is read as `urllib.robotparser` does: 200 is parsed, 401 and 403 forbid everything, any other 4xx allows everything. A 5xx answer or a failed request fails the source, because the tool cannot tell whether it may fetch. Redirects of robots.txt itself are followed.
- **Redirects of the article are followed by hand, at most five.** A redirect to another site triggers that site's robots.txt check before the request. Only the redirect chain of the given URL is followed; links in the page never are.
- **Refusals:** 401, 402 and 403 are reported as a paywall or login; 404 and 410 as a wrong address; 429 as a request to slow down. Every message points to the `.txt` fallback where that helps.
- **Main text** comes from trafilatura's `bare_extraction` without comments and tables. The headline is dropped when it repeats the title. A content type that is neither HTML nor XML fails.
- **Fewer than 150 words of main text fail the source** as a likely paywall teaser, login page or non-article. The floor is a constructor argument of `NewsUrlSource`, not a setting.
- **Timeout** 20 seconds per request. Timeouts and network errors fail only that source.

## Alternatives considered

- **Let httpx2 follow redirects:** simpler, but a redirect to another site would be fetched without asking that site's robots.txt.
- **Treat a robots.txt server error as "allowed":** some crawlers do; RFC 9309 says to assume a full disallow, and failing the source with a retry hint is the polite reading.
- **Detect paywalls by markup** (`paywall` classes, schema.org `isAccessibleForFree`): varies by site and needs upkeep; a word floor catches teasers on any site.
- **A configurable floor:** no need seen yet; it can become a setting if real articles are rejected.

## Consequences

- Short real articles (news briefs under 150 words) are rejected and must be added as `.txt`. The owner's manual check with real URLs shows whether the floor is right.
- Every site costs one extra request per command for robots.txt.

## Related

- [Ingest](../system-design/ingest.md)
- [0013 Fetch articles politely, without bypassing paywalls](0013-fetch-articles-politely-without-bypassing-paywalls.md)
- [0027 Settle runtime dependencies up front](0027-settle-shared-dependencies-before-parallel-tracks.md)

# 0007. Keep hourly summaries for 3 months, and review their value as we go

- **Status:** Accepted
- **Date:** 2026-11-14
- **Issue:** PonchoAndy/DayTrader#26

Refines the "hourly summaries: a few months" retention in [0005](0005-hourly-collection-on-github-actions-with-object-storage.md).

## Context

Pricing item variants separately (#30) more than doubled the hourly summaries: about 107k rows and
1.3 MB per snapshot, roughly 0.9 GB a month. The daily roll-up (#26) will hold the long-term history.
The question was how long the detailed hourly tables are worth keeping.

## Decision

- Keep **hourly summaries (`hourly/`) for 3 months** (about 2.7 GB at today's size), deleted
  automatically by an R2 lifecycle rule.
- Prefer detail over the cheapest option, but don't keep data with no use.
- **Review during the first 3 months:** note each time analysis actually needs hourly detail (e.g.
  time-of-day patterns, short-lived deals). If it rarely does, shorten the retention.
- Daily summaries stay indefinitely (0005). Raw pulls stay 7 days.

## Consequences

- Storage is about 1.6 GB raw + 2.7 GB hourly + small daily files, within R2's free 10 GB.
- A lifecycle rule on `hourly/` (90 days) is needed. It's set in the Cloudflare dashboard.
- The review becomes a follow-up around 2027-02-14.

## Alternatives considered

- **Keep hourly forever:** ~11 GB a year and growing, mostly unused once daily summaries exist.
- **1 month:** cheaper, but too short to judge whether hourly detail pays off.

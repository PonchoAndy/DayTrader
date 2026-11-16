# 0014. A trading day starts at 12:00 UTC (7am US Eastern in winter)

- **Status:** Accepted (owner, 2026-11-16, on #44 and in chat: "7am", time zone Eastern)
- **Date:** 2026-11-16
- **Issue:** PonchoAndy/DayTrader#44

## Context

The daily roll-up (#26) and every "per day" figure (sales per day, daily lows) need a cut-off hour.
Our data so far shows the busiest trading in the US evening, about 05:00–07:00 UTC. A cut-off inside
that window would split one evening's trading across two days. The agents suggested 10:00 UTC, the
quietest hour. The owner asked for about 7am their time (US Eastern): an hour they'll never play across,
since they often trade after midnight.

## Decision

- A trading day runs from **12:00 UTC to 12:00 UTC** the next day: 7am Eastern in winter (EST), 8am
  during summer time (EDT). The hour is fixed in UTC, so it never moves with daylight saving.
- A day is named by the date on which it **starts**: the "2026-11-16" trading day runs from
  2026-11-16 12:00 UTC to 2026-11-17 12:00 UTC.
- Listing flows stay stored per UTC calendar date (ADR 0008). The roll-up groups their hourly rows
  into trading days.
- Re-check against two weeks of data, then again when Europe or other regions get their own daily
  views. Europe may want its own cut-off; this decision is for US views.

## Consequences

- The daily roll-up (#26) and the Analyst's daily tests use this boundary.
- A night's trading after midnight Eastern counts in the same day as that evening.
- Changing it later means recomputing daily summaries, which is possible while hourly data is kept
  (90 days).

## Alternatives considered

- **10:00 UTC** (agents' first suggestion, ~5am Eastern): also quiet, but not tied to the owner's routine.
- **Midnight UTC** (7pm Eastern): splits the busy US evening.
- **Weekly maintenance hour:** a natural break, but weekly, not daily.

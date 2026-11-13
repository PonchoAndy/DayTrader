# 0003. US region, Horde primary, collect every auction house

- **Status:** Accepted
- **Date:** 2026-11-13
- **Issue:** PonchoAndy/DayTrader#2

## Context

The Forever API groups auctions by region and ruleset. US and EU each have four rulesets
(PvP, Normal, Roleplay, Roleplay PvP), and each ruleset lists 15 houses: five each of Alliance,
Horde and neutral (Blackwater). Right now every ruleset in a region returns identical houses.

Your answer on #2: US only. Normal ruleset. Trade Horde primarily, but don't limit the system
to one faction; collect Alliance and all rulesets if the overhead is acceptable.

## Decision

- Collect from the **US** region only (`us.api.blizzard.com`, `dynamic-forever-us`).
- Collect **all 15 houses** (Alliance, Horde, neutral) every run.
- Query through the **Normal** ruleset. Since all rulesets currently return the same data,
  fetching each ruleset separately would only duplicate it. Re-check periodically; if rulesets
  start returning different data, collect each one.
- **Horde** is the default view everywhere. Faction (and ruleset) are settings in the data
  model and dashboard, never hard-coded.

## Consequences

- About 30 API calls per hourly run: far below Blizzard's limits.
- Roughly 3x the storage and run time of a Horde-only pull (busiest houses are ~9 MB each).
  Mitigated by storing per-item hourly summaries rather than every raw pull (see 0005).
- Cross-faction comparisons (price gaps between Horde, Alliance and neutral) come for free.
- Every stored row needs region, ruleset, house and faction columns.
- The collector must not sum across rulesets while they return identical data.

## Alternatives considered

- **Horde only:** less storage, but switching later would mean no history for Alliance.
- **EU too:** not needed.

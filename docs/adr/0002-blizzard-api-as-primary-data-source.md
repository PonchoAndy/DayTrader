# 0002. Blizzard Game Data API as the primary data source

- **Status:** Accepted
- **Date:** 2026-11-13
- **Issue:** PonchoAndy/DayTrader#9 (first test of the API)

## Context

There are two ways to get WoW Forever auction data:

1. **Blizzard's Game Data API.** Undocumented for Forever, but community developers confirm it
   has served auction data since 2026-11-06: `/data/wow/ruleset/{id}/auctions/` (trailing
   slash required) lists 15 houses, each with its own auctions and commodities, in the
   `dynamic-forever-us` namespace. Free, needs only a client ID and secret.
2. **An in-game addon scan**, the way Auctionator works: a full scan with
   `C_AuctionHouse.ReplicateItems()`, saved to a `SavedVariables` file on disk. Addons can't
   make network calls, so the data only leaves the game through that file.

## Decision

Use the Blizzard API as the primary source. Consider a small addon later, only to fill gaps
(item names the API is missing, your own purchases and sales).

## Consequences

- Collection runs unattended in the cloud; nobody needs to be logged in.
- We depend on an undocumented API that may change without notice. The collector should
  fail loudly and save raw responses so we can adapt.
- The API shows listings, not sales. Sale rates must be estimated by comparing hourly
  snapshots, which is noisy (a vanished listing may have sold or been cancelled).
- About 43% of auctioned item IDs are missing from Forever's item data, so item names need a
  fallback source.

## Alternatives considered

- **Addon only:** needs you in game, is throttled (about one full scan per 15 minutes) and
  manual. Rejected as the main source.
- **Third-party price sites (wowauctionhouse.com, TSM API):** convenient, but we'd inherit their
  methods, gaps and terms. Useful for cross-checking only.

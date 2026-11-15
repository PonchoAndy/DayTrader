# 0012. Home house is 114 (US Normal Horde); the ruleset comes from the house ID

- **Status:** Accepted (owner, 2026-11-15, option "a" on #85)
- **Date:** 2026-11-15
- **Issue:** PonchoAndy/DayTrader#85 (research: `docs/designs/2026-11-15-which-house.md`; check: #13)

## Context

ADR 0003 made "Normal ruleset, Horde" the primary market, but we didn't know which of the 15 auction
houses that is. The API can't say: any ruleset ID returns all 15 houses, and a house carries no ruleset
field. Several docs and mock-ups used **113** (the biggest Horde house) as "your house".

The Researcher found the mapping in Forever's own game files (wago.tools `AuctionHouseRedirect` +
`AvailableSuperDistrict`, build 1.60.1.70938) [datamined]: each ruleset has its own Alliance, Horde and
Blackwater house. PvP 110/113/116 · **Normal 111/114/117** · Roleplay 119/120/121 · Roleplay PvP
123/124/125 · Hardcore 112/115/118 (not open, empty). Mail between rulesets is blocked. Prices differ
between houses (e.g. Frilled Lichen 17.7s on 114 against 27s on 113, 2026-11-15 22:17 UTC).

## Decision

- The owner's **home house is 114** (US, Normal, Horde). Reachable markets: 114, then Blackwater **117**
  (15% cut, higher deposit). Analyses, the Stockpile Ledger's prices and future advisors default to 114.
- **A row's ruleset is taken from its house ID** using the table above, never from the ruleset ID used
  in the API call.
- Re-check the redirect table each game build (cheap: one CSV fetch), since Blizzard may link houses
  if a ruleset dries up.
- The in-game marker listing on #13 confirms it; if it shows otherwise, this ADR is superseded.

## Consequences

- Docs and mock-ups that call 113 "your house" get switched to 114 (follow-up): the presentation spec's
  T1 example, the item-page mock-up, the strategy-intents "wrong house" example, the stockpile review's
  exit-capacity figures, the overnight demo, and the Economist's EU-113 comparisons (pair EU-114 with US-114).
- The proposed daily roll-up (`docs/designs/2026-11-14-analysis-layer.md`) must label rows by house, so
  113 reads "PvP", not "Normal".
- ADR 0003 stands; this ADR fills in which house it means.

## Alternatives considered

- **Keep 113:** the biggest Horde house, but the owner can't trade on it.
- **Wait for the marker check first:** safer, but the game files, house sizes and price patterns already
  agree, and the owner is trading on 114 now.

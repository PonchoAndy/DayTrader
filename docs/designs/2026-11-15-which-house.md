# Which auction house is the owner's? — Researcher (2026-11-15)

Saved by the main session from the Researcher agent's report (ADR 0010). The house map itself is in PLANNING §1, "What a house is".

## Answer
- **The owner's house (US, Normal ruleset, Horde) is 114**, per Forever's own game files. Reachable markets: 114, and Blackwater **117** (15% cut, higher deposit).
- **Confidence: likely, close to firm.** Three things agree: the redirect table, the ruleset table it points to, and house sizes (Hardcore's houses are empty). An in-game marker listing makes it firm (Check A).
- **It matters:** the owner can only trade on 114/117, so every price, deal, cap, stock limit and position value must come from 114. Several docs and mock-ups treat 113 (PvP Horde, unreachable) as "your house".

## Findings
- **F1 [datamined, build 1.60.1.70938]** `AuctionHouseRedirect` (wowf) rows `(base AH, key, Alliance target, Horde target)`; bases 2 Alliance, 6 Horde, 7 Blackwater, 122 generic "Auction House". Keys: 2 → 110/113/116 · 3 → 111/114/117 · 4 → 119/120/121 · 5 → 112/115/118 · 7 → 123/124/125.
- **F2 [datamined]** The key is `AvailableSuperDistrict.ID` ("super district" = ruleset): 2 PvP (API 1), 3 Normal (API 2), 4 Roleplay (3), 5 Hardcore (4), 6 CN Beta Event (7), 7 Roleplay PvP (15). The API ruleset IDs match exactly. Client files: the server decides, so one marker check confirms.
- **F3 [official, Blizzard "Choose Your Ruleset", 2026-09-21, updated 10/22]** Five rulesets; no cross-ruleset grouping; can't hop rulesets; one faction per account on PvP. No mention of the AH.
- **F4 [our data, API probe 2026-11-15]** Ruleset index returns 1, 15, 3, 2 (Hardcore 4 is 404). Houses have only `id`, `name`, and a `ruleset` link echoing the query. Every ruleset returns the same listings (tiny count differences look like separate caches).
- **F5 [our data]** Listing IDs come from one region-wide counter, so they can't group houses into worlds.
- **F6 [datamined, GlobalStrings]** "You can't send mail to that ruleset." The paid-transfer screen has a destination-ruleset field, but Blizzard says rulesets can't be changed (dead Hardcore characters excepted).
- **F7** Blackwater is the only way across factions on a ruleset (117 for Normal).
- **F8 [datamined, open lead]** A fifth house, "Auction House" (ID 122), has Blackwater rates but sends each faction to its own ruleset market. Where it is, and which cut applies there, is unknown.
- **F9** wowauctionhouse.com's labels agree where testable (matched by exact prices), but its method is undocumented and may rest on the same table.
- **F10–F11** A forum claim that "all but Hardcore share an auction house" is contradicted by our data. Press snippets report Blizzard may link houses if a ruleset dries up, so re-check the table each build.
- **F12 [our data, 22:17 UTC]** The 113/114 gap changes by the hour: Pyrite 1.79s vs 1.50s; Pristine Leather currently cheaper on 113; Frilled Lichen 27.0s vs 17.7s.

## What goes wrong with the wrong house
Deals and caps judged on an unreachable market; ledger values inflated by up to ~50–85% for Lichen/Pyrite; "hold no more than is listed" uses another market's supply; sale-rate, depth and undercut figures describe other players' competition; EU-vs-US comparisons should pair EU-114 with US-114.

## Owner checks
- **Check A (conclusive, ~1s, ~3 min):** post 1 Linen Cloth at a buyout of exactly **9g 87s 65c** for 24 h; note the time; leave it up ≥2 h (data publishes at :17); reply on #13 with item, price and time. Expected: it appears only on 114. Optional: same at Booty Bay → expected 117.
- **Check B (quick, not conclusive):** Frilled Lichen's cheapest price: ~18s fits 114, ~27s fits 113 (22:17 UTC).

## Conflicts to fix
- PLANNING §1, line 19, §3: updated 2026-11-15.
- ADR 0003 stands, but its "every stored row needs ruleset" must take the ruleset **from the house ID**. Suggested new ADR: home house 114, ruleset derived from house ID.
- `docs/designs/2026-11-14-analysis-layer.md` daily-table example labels 113 as Normal (roll-up not built yet).
- 113 used as "your house": `2026-11-15-presentation-spec.md` (T1 example reversed), `docs/mockups/2026-11-15-first-views/item-page.html`, `2026-11-15-strategy-intents.md`, `2026-11-15-stockpile-positions-review.md` §6, `tools/overnight-demo/`, the Economist doc's EU-113 comparisons.

## Hypotheses for the Analyst
- **H-W1:** 112/115/118 stay empty until Hardcore opens, then fill together, and ruleset 4 appears in the API.
- **H-W2:** the owner's marker listing appears only on 114 (checkable live from a session after the next :17).
- **H-W3:** the PvP price gap (= H-E2), with Roleplay vs Roleplay PvP as a control.
- **H-W4:** if Blizzard links houses, one falls to ~0 as its partner jumps, and `AuctionHouseRedirect` changes. Re-fetch it weekly with `bonuses.py`.

## Sources
wago.tools `AuctionHouseRedirect`, `AvailableSuperDistrict`, `AuctionHouse`, `Cfg_SuperDistrict`, `GameMode`, `GlobalStrings` (branch `wowf`, build 2026-11-13); WoWDBDefs `AuctionHouseRedirect.dbd`; Blizzard news 24302070 (rulesets); Blizzard Game Data API probe 2026-11-15; Blizzard forums t/60334 and t/2392185; wowauctionhouse.com; wowcampfire.com, playnews.gg, pcgamesn.com (snippets only, blocked).

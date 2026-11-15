# Data requirements catalog, v1 (2026-11-15)

The Strategist agent's first job (`.claude/agents/strategist.md`, PonchoAndy/DayTrader#39): what data
a trader needs to see, across every kind of player, checked against what we collect and against
[ADR 0008](../adr/0008-analysis-layer-daily-rollup-listing-flows-versioned-metrics.md) before the
listing-flows build (#37). The Architect designs against this document. **The owner can edit it**;
strike or change anything before it's used.

## Review notes (main session)

- **Checked and right:** the deadlines. Raw pulls from 2026-11-14 ~01:05 UTC, kept 14 days, expire
  ~2026-11-28; the first hourly files expire ~2027-02-12 (90 days). It showed the working this time,
  which is one of the fixes made to the Architect after its first run.
- **Checked and right:** Copper Ore is ~0.02 g (2 silver) in PLANNING, so a 5-silver floor would hide
  it. It used real figures for its examples.
- **It corrects the Architect:** ADR 0008 called the day boundary "can't be undone". Daily figures
  can be rebuilt from hourly data and flows for 90 days, so it isn't urgent.
- **Couldn't verify:** TSM's formulas (the TSM site was blocked by this session's network settings),
  the 2026-11-10 hotfix details (cited to Blizzard's forum and news sites), and several "from memory"
  items, which it flagged and turned into hypotheses.
- **Slight drift into design:** suggestions like a weekly hour-of-day profile and floors measured
  in gold per trade are close to the Architect's job. They're reasonable requirements, so they stay.

---

## Part 1: For the owner

### 1. Summary

1. Listing flows (ADR 0008) will tell us how much sold. A trader also needs to know **at what price it sold, how fast it sold, and how much sits near the cheapest price**. Today none of those survive once the raw pulls are deleted.
2. Four extra measures should be taken from the raw pulls in the same daily job, before the oldest pulls expire around **2026-11-28**:
   - **Depth near the cheapest price:** how many units, and how much gold, sit within a few percent of the cheapest listing.
   - **Where each vanished listing sat:** at the cheapest price, close to it, or far above it.
   - **How long it was up before it vanished.**
   - **How often new listings undercut the cheapest one.**
3. The biggest outside need is **game data**: recipes and their reagents, vendor prices, and item level and required level. Without it the profession, crafting, gathering and level-range choices can't work. All of it can be fetched at any time, so it isn't urgent.
4. **Fees must be confirmed in game (#13)**: the cut, the deposit, listing durations, and which houses are "yours". Every profit number depends on them.
5. Two of ADR 0008's settings work against some players:
   - The **5-silver price floor** would hide cheap, high-volume leveling materials like Copper Ore (about 2 silver).
   - A **once-a-day page refresh** can't serve "buy right now" decisions.

### 2. Collect now or lose

| What | Why it's lost | Deadline |
|---|---|---|
| **Raw-only measures** (depth near the cheapest price, where vanished listings sat, how long they were up, undercut counts, time-left mix of current supply, which price buyers took for commodities) | Listing IDs and per-listing prices exist only in `raw/`. The first stored snapshot is `20261114T0017Z`, and raw is now kept 14 days (#38). | Oldest hour gone about **2026-11-28**, then one more hour every hour. If raw goes back to 7 days after the #37 backfill, the window shrinks to 7 days. **Decide what the flows job captures before setting raw back to 7.** |
| **Missed hours** | Blizzard only serves the latest snapshot. Two of 13 hours were lost on 11-14 (#28). Each gap also blurs flows: anything posted and sold inside the gap is invisible. | Ongoing. The fix (a second schedule slot) is waiting on the owner's OK in #28. |
| **Time-of-day patterns over the long term** | The daily roll-up keeps the day's low, median and high, but not *when* they happened. Hourly data expires after 90 days. | Rolling. The first hourly files expire about **2027-02-12**. A small "typical price by hour of day" profile, saved per week, would keep the pattern forever. |
| **Launch-week market (11-06 to 11-13)** | Collection started 11-14. | Already lost. Third-party sites (wowauctionhouse.com, which claims hourly Forever scans) might have it. Unverified. |
| **Game events** (hotfixes, phases, maintenance) | Patch notes stay online, but matching them to price moves is easiest if they're logged as they happen. Example: the 11-10 hotfix notes announced a 1-copper minimum deposit (it was pulled and is due 2026-11-17, Europe 11-18) and added quest gold from level 48 up. | Low urgency. Start a simple event log now. |

Not lost, and safe to wait: recipes, vendor prices and item levels (game data can be fetched any time), and all formulas (ADR 0008 keeps ingredients).

### 3. What each player choice needs

**Faction and auction house.** A player can only trade where their character is, so every number has to be per house. That's already the rule. Two things are missing:
- **Which houses are "mine"**, and which Blackwater house each faction house connects to. This is unknown and needs the in-game check in #13.
- **For Blackwater bridge trades:** the other faction's home price (we have it), Blackwater's own sale rate (from flows), Blackwater's cut (reportedly 15%, unconfirmed), and the trip to Blackwater as a time cost.

The small Blackwater houses (116, 117 at 6–7k listings) mean bridge trades need a sell-through check, not just a price gap.

**Professions.** This needs outside data: each recipe's reagents and amounts, its product and how many it makes, the profession and skill level, how the recipe is learned, and which reagents vendors sell and for how much. For Enchanting, it also needs disenchant outcomes. With that, the app can show reagent cost against product price, and the product's sale rate.

Gatherers need different things: price, how much the market absorbs per day (so their farm doesn't crash the price), the best hour to sell, and the vendor sell price as a floor. Guide sites say Forever's profession list and balance aren't settled yet.

**Budget.** This needs:
- **Depth:** gold needed to buy N units, or to buy everything up to a price.
- **Capital lock time:** how long until it sells, from listing age at vanishing.
- **Deposit at risk**, which needs each item's vendor sell price and the confirmed deposit rule.
- **Market share:** your planned stack against units sold per day.

Today only percentiles (p10, p25) stand in for depth. That's not enough for "can I buy 200 at this price?".

**Playtime.** This needs how long deals survive (in hours), how often the cheapest listing gets undercut, the best hours to buy and sell, and the listing durations Forever offers. A player who visits once a day can't use a deal that lasts an hour, and can't hold the cheapest spot on an item that's undercut every hour. API data is at best about 1–2 hours old by the time you see it (Blizzard refreshes hourly, and our pull lands a median 44 minutes later). True real-time sniping can't be done with this data. What we can offer instead: deals that last several hours.

**Risk appetite.** This needs:
- **Volatility:** hour-to-hour and day-to-day swing (in ADR 0008).
- **Trend:** whether the price is falling, so "below normal" isn't a falling knife.
- **Sell-through:** the chance a listing sells rather than expires (in ADR 0008).
- **The fill rate at each price position:** does a listing 10% above the cheapest ever sell?
- **Supply concentration:** a few big listings versus many small ones.
- **For cornering:** how fast new supply arrives, which comes from flows.

**Extra criterion: level range and game phase.** Forever looks like a level-60 game, with quest gold from 48 and up per the 11-10 hotfix. Demand for leveling materials (Copper Ore, Red Wolf Meat, ammunition) probably shifts as players level up. This needs each item's required level and item level, which our item lookups already receive but don't save, plus long-run daily sale rates and an event log.

### 4. Open questions for the owner

1. **Should the flows job also save the raw-only measures in section 2?**
   - (a) Yes, as summed counts per item per hour.
   - (b) Keep a slim record of every listing for 90 days (ADR 0008's Option C, about 4 GB).
   - (c) No.
   - **Suggested default: (a).** Option (b) stays in reserve if the Analyst's tests show (a) isn't enough.
2. **When should raw go back from 14 to 7 days?**
   - (a) Right after the #37 backfill.
   - (b) After the extended measures are also backfilled and Analyst tests H3 and H17 have run.
   - **Suggested default: (b).** It costs about 1.5 GB for a couple of extra weeks.
3. **Add the second schedule slot (#28)?**
   - **Suggested default: yes.** Missed hours are lost for good and weaken sale-rate estimates.
4. **Where should recipe and vendor data come from?**
   - (a) wago.tools, Forever's own game tables (branch `wowf`), the same place the variant names came from.
   - (b) Wowhead.
   - (c) A hand-made list.
   - **Suggested default:** (a), with Wowhead only to fill gaps such as vendor stock and disenchant rates, after checking its terms.
5. **Which professions first?**
   - **Suggested default: all.** Once the game tables load, the cost of adding each one is about the same. The player's selection filters the view.
6. **Price floor: one global setting, or each player's own?**
   - **Suggested default: the player's own,** with the page export left unfiltered. Measure floors as gold per trade, not price per unit, so cheap high-volume materials stay visible.
7. **Normal-price window: 7 or 14 days?**
   - **Suggested default: 7 days,** plus a short 3-day figure and a trend flag. This can be changed for free later.
8. **When does a day start?**
   - **Suggested default: 10:00 UTC for now,** checked against two weeks of data. It can be redone for up to 90 days, so it isn't urgent.
9. **How often should pages refresh?**
   - **Suggested default: two speeds.** "Right now" views show the latest hour. Strategy views (crafting, Blackwater, trends) refresh daily or on demand.
10. **The in-game check in #13: can the owner also note these?**
    - Listing duration choices.
    - Whether a cancelled listing's deposit is refunded.
    - Whether buying a commodity always takes the cheapest units first.
    - Which cities share listings.

---

## Part 2: Requirements catalog

### 5. Catalog table

Statuses:
- **Have:** already collected.
- **Derive:** computable from what we have.
- **New:** needs a new outside source.
- **CNL:** collect now or lose.
- **Can't:** not available; a stand-in is named.

Criteria:
- **F:** faction or house.
- **P:** professions.
- **B:** budget.
- **T:** playtime.
- **R:** risk.
- **L:** level or phase.

Value, cost and urgency are rated H (high), M (medium) or L (low).

| # | Decision | Signal | Data needed | Status | Criteria | Value / Cost / Urgency | Priority |
|---|---|---|---|---|---|---|---|
| 1 | What should I buy right now? (flip) | Deal % = current cheapest ÷ normal price | Latest hourly min and p10, daily p25 history | Have / Derive | all | H / L / L | Must |
| 2 | Is this deal real or a falling knife? | Normal price plus trend (3-day vs 7-day), day-to-day swing | Daily roll-up | Derive | R | H / L / L | Must |
| 3 | Will it resell, and how fast? | Units sold per day, sell-through | Flows (ADR 0008) | CNL (in #37) | B, T, R | H / M / H | Must |
| 4 | At what price does it actually sell? | Units vanished early by price position against the previous hour's cheapest (at the cheapest, within 5%, within 20%, above) | Per-listing price and the previous hour's cheapest, from raw | **CNL, not in ADR 0008** (it has only "≤ p25" and a capped value) | B, R, T | H / L / **H** | Must |
| 5 | What price did buyers really pay? | Value of partial buys (certain sales), kept apart from early vanishings | Raw | **CNL** (ADR merges partial-buy value into `gone_early_value`) | R | M / L / H | Must |
| 6 | Sold or cancelled? (sharpens #3) | For commodities: a listing that vanished while cheaper ones stayed untouched was most likely cancelled | Raw; assumes buyers take the cheapest first (H4) | **CNL** | R | H / L / H | Must |
| 7 | How long is my gold locked? | Hours from first sighting to vanishing, in bands (<2 h, 2–12 h, 12–24 h, 24–48 h) | Listing first-seen time across hours, which may span days | **CNL** (ADR compares consecutive hours only) | B, T | H / M / H | Must |
| 8 | Can I buy N units at this price? (depth) | Units and gold within +2%, +5%, +10%, +25% of the cheapest; cost to buy everything up to a price | Raw price ladder per item | **CNL** (percentiles are only a partial stand-in; see H13) | B, R (cornering) | H / L / H | Must |
| 9 | How crowded is the cheapest spot? | Listings within 1% of the cheapest; size of the biggest listing there | Raw | **CNL** | T, R | M / L / H | Should |
| 10 | How often will I be undercut? | New listings priced below the previous cheapest, per hour; how many hours the cheapest price holds | Raw (new listings with prices) | **CNL** | T | H / L / H | Must |
| 11 | Will supply drop soon? | Share of current units in SHORT or MEDIUM time-left | Raw `time_left` | **CNL** (hourly summary has no time-left) | T, R | M / L / H | Should |
| 12 | Which listing durations exist, and what do sellers choose? | `time_left` of brand-new listings | Raw | **CNL** (needed to read expiries correctly) | T | M / L / H | Must |
| 13 | Is the market flooded or short? | Latest quantity ÷ typical quantity | Hourly, daily | Have / Derive | R | M / L / L | Must |
| 14 | Can I corner it? | Gold to buy out supply up to a target, new units posted per day, resell time | #8, flows, #7 | Derive after CNL | B, R | M / L / H | Should |
| 15 | When should I buy and sell during the day? | Typical p10 and units sold by hour of day and day of week | Hourly (90 days); a weekly hour-of-day profile for the long run | Derive; **rolling loss** after 90 days | T | M / L / M | Should |
| 16 | How long does a deal last? | Hours a listing ≤70% of normal stays up | Raw (listing survival) | **CNL** | T | H / L / H | Must |
| 17 | Which house is mine; which Blackwater do I reach? | House-to-city/world mapping | In-game check (#13) | New (in game) | F | H / L / M | Must |
| 18 | Same-faction house gaps | Price gap between houses (Black Lotus 10 g vs 17.89 g) | Hourly | Have | F | M / L / L | Should (only if a player can reach several houses) |
| 19 | Blackwater bridge trade | Other faction's home p25 minus my cost, after the 15% cut and deposit, with Blackwater sell-through | Hourly, flows, fees | Derive plus New (fees) | F, B, T | H / L / M | Must |
| 20 | Is the profit real? | Net of cut and deposit | Cut % per house type; deposit rule; vendor sell price; refund rules | New (in game #13; game data) | all | H / L / M | Must |
| 21 | Is crafting X profitable? | Product price × (1 − cut) − sum of reagent prices (vendor price if vendor-sold) | Recipes, reagents and amounts, product amount, vendor-sold reagents and prices | New (game tables) | P, B | H / M / L | Must |
| 22 | Can the market absorb my crafts? | Product units sold per day, sell-through | Flows | CNL (in #37) | P, T | H / – / H | Must |
| 23 | Which profession should I level? | Total margin × volume across the recipes available at each skill level; cost to level | Recipe skill levels, how recipes are learned, #21, #22 | New plus Derive | P, L | H / M / L | Should |
| 24 | Disenchant or sell? | Expected disenchant value vs the item's price | Disenchant outcome rates | New (community-measured; Wowhead) | P | M / M / L | Later |
| 25 | What should I farm? | Price × absorbable volume; best hour to sell; vendor floor | Flows, hourly, vendor sell price; node or zone and level | Derive plus New | P, T, L | H / L / L | Should |
| 26 | Gold per hour farming | Farm rate | Not available | Can't. Stand-in: the player's own reported rate. | P, T | M / – / – | Later |
| 27 | What will rise next? (speculation) | Long-run trend, first-seen date per item, sale rate by level band, event log | Daily (forever), item required level, event log | Derive plus New | R, L | M / L / M | Should |
| 28 | Who is selling? | Seller identity or count | Not in the API | Can't. Stand-in: listings at the cheapest, listing-size patterns, repost guess. | R, T | M / – / – | — |
| 29 | Real-time sniping | Minute-level listings | API is hourly | Can't. Stand-in: deals that survive (#16). In-game scanning (Path B) would be manual. | T | M / – / – | — |
| 30 | Which version of an item? | Variant suffix | Have (#30) | Have | all | M / L / L | Must |
| 31 | Do I trust this number? | Hours covered, missed-hour flags, confidence | Collector run logs, `hours_in_day` | Have / Derive; missed hours are CNL (#28) | all | H / L / H | Must |
| 32 | Is there a deal on gear I can use? | Required level, item level, equip slot | Item API fields already received but not saved | New (cheap re-fetch) | L, B | M / L / L | Should |
| 33 | Does auction `modifiers` or `context` change price? | Price spread by those fields | Raw only (dropped by the summaries) | **CNL to check once** | — | L / L / H | Should (one check) |
| 34 | Bids | Bid-only auctions (0.2%) | Raw | Fine to drop | — | L / – / – | — |

### 6. New data sources

| Source | What | Where | Trust | Changes |
|---|---|---|---|---|
| Forever game tables | Recipes (profession and skill line, spell, reagents and amounts, product and amount), item vendor buy and sell prices, item level and required level | wago.tools, branch `wowf`. It already worked for bonus names. The table names (SkillLineAbility, SpellReagents, SpellEffect, ItemSparse) are memory of retail and Classic and need checking. | High: extracted from the client. Server-only facts (vendor stock, drop rates) aren't in it. | Each game build; weekly refresh is enough |
| Blizzard item API (fields not saved yet) | `sell_price`, `purchase_price`, `level`, `required_level` (from memory; check one response) | Already called by `items.py`, which keeps only name, quality and class | Official, but Forever's database covers about 57% of IDs, with retail filling the gap. Retail values may differ from Forever's. | Rarely |
| In-game checks (#13) | Cut, deposit formula and refund rules, listing durations, house-to-city mapping, Blackwater linkage, commodity buy order, same-account limits at neutral houses | The owner, in game | Highest for Forever | On hotfixes |
| Wowhead or similar | Vendor stock (which NPC sells a reagent), disenchant rates, gather node zones | Web; check the terms before scraping | Community-measured; may lag Forever | Occasional |
| Event log | Hotfixes, maintenance, phase releases | Blizzard hotfix posts (official); news sites | Official, or community news summarizing it | Weekly |
| Third-party history (optional) | Launch-week prices | wowauctionhouse.com, Undermine Exchange (check whether they cover Forever) | Unknown | One-off |
| Player's own trades (later) | Actual buys and sales, for measuring advice | Path B addon or manual entry | High for that player | Per session |

### 7. Gaps in current plans

1. **ADR 0008 flows keep only how many sold, not how.** They miss the price position of vanished units (#4), listing age (#7), undercut events (#10) and deal survival (#16). All four need raw data and fit the same daily job. Listing age needs first-seen times carried across day boundaries. Matching consecutive hours alone can't give it.
2. **Partial-buy value is merged** into `gone_early_value`. Partial buys are the only certain sale prices, so they should be kept separately (#5).
3. **The cheapest-first rule is unused** (#6). If Forever commodities fill cheapest-first, it is the strongest clue for telling sales from cancels, and it needs raw data. Test it before relying on it (H4).
4. **No depth or time-left in hourly or daily data** (#8, #11). Percentiles can't answer "how much does 200 units cost?". H13 tests whether p10 is a good enough stand-in.
5. **Penny floor (5 silver normal price, 0.20 g per unit):**
   - It hides Copper Ore (about 0.02 g) and similar leveling materials, which PLANNING names as the most-bought items.
   - Floors should measure gold per trade (depth × margin) and be player settings.
   - The app export should not pre-filter on one floor.
6. **One normal-price window with no trend.** In a 10-day-old trending economy, a 7-day median lags, so falling items look like deals. Add a short window and a trend flag. These are cheap and come from the daily data.
7. **Day boundary marked "can't be undone".** It can be redone from hourly data for 90 days and from flows for 90 days, so it isn't urgent. The trader's view: keep one US evening (peak about 05:00–07:00 UTC) inside one day. 10:00 UTC does that. Confirm the quietest hour with two weeks of data. The weekly reset or maintenance hour is worth checking as an alternative.
8. **A daily page refresh only.** Fine for crafting, Blackwater and trend views. Useless for deals (#1, #16), which need the latest hour; the hourly data is already about 1–2 hours old when seen.
9. **Long-run time-of-day pattern.** #33 asks whether hourly data is worth keeping. A compact weekly hour-of-day profile would make that question less pressing.
10. **`items.parquet` drops fields** needed for fees, vendor floors and level range (#20, #32).
11. **Missed hours** (#28) aren't just gaps in prices. They blur flows. The second slot is a data-quality need, not a nicety.
12. **Over-collection is minimal.**
    - `max_price` is unused by metrics but tiny.
    - Bids can stay dropped.
    - The empty houses cost almost nothing.
    - Raw at 14 days is worth keeping until the extra measures are backfilled.

### 8. Hypotheses for the Analyst

These must be checked on our data before anything is built on them. **H1–H5, H13, H17 and H18 need raw data, so run them before about 2026-11-28.**

| # | Claim | Test |
|---|---|---|
| H1 | A partly bought commodity listing keeps its ID. | Already in #37: match IDs where quantity fell. |
| H2 | Forever's time-left buckets match its listing durations, and a vanish in SHORT means it expired. | Look at the `time_left` of new listings, and at how long listings last from first sighting to vanishing, per bucket. |
| H3 | Early vanishings at or near the cheapest price are mostly sales; those far above it are mostly cancels. | Compare early vanishings by price position. Check repost matches and whether cheaper listings stayed. |
| H4 | Commodity buys take the cheapest units first (memory of retail). | For an hour with vanished units, check that no cheaper listing survived untouched. Also confirm in game (#13). |
| H5 | Deep-discount listings (≤70% of normal) often last ≥1–2 hours, so an hourly player can act on them. | Survival curve of such listings by item price band. |
| H6 | The 70%-of-market threshold (PLANNING §3, guide source) finds trades that resell higher. | Compare the deal price with the p25 seven days later, net of a 5% cut, plus sell-through. |
| H7 | Intraday price cycles are bigger than the cut. | Swing of p10 by hour of day over 2 or more weeks, per item band. Is it above 5% after noise? |
| H8 | Same-faction houses are separate markets. | Persistence of price gaps between houses over days; then the in-game check (#13). |
| H9 | Blackwater bridge trades actually sell. | Blackwater sell-through for items where the bridge margin is positive. |
| H10 | % moves under about 5 silver are price-step noise. | Swing % against price level, counted in copper steps. |
| H11 | Leveling-material demand fades as players level. | Trend in daily sale rate for low-level materials over 4–8 weeks. |
| H12 | Guides' claims that Alchemy and Enchanting are strong (guide-seller sources) | Recipe margin × sale rate once recipe data exists. |
| H13 | Percentiles (p10) are a good stand-in for depth. If true, depth needn't be stored. | On raw data, compare the cost to buy N units with the p10 estimate. |
| H14 | Weekly maintenance or reset shifts supply and prices. | Day-of-week and hour effects around the weekly restart. |
| H15 | A variant's suffix premium is stable. | Variant price ÷ base price over days. |
| H16 | Supply's overnight drain is mostly expiries, not sales (PLANNING) | Flows: gone-early vs gone-short units overnight. |
| H17 | Undercutting is frequent on busy commodities, so low-playtime sellers lose the cheapest spot. | Hours the cheapest price holds, by house size. |
| H18 | `modifiers` and `context` don't affect price. | One pass over raw before it expires. |

### 9. Sources and files read

**Files:**
- `CLAUDE.md`
- `docs/PLANNING.md`
- `collector/README.md`
- `collector/collect.py` (summary code)
- `collector/items.py`
- `docs/adr/README.md`, 0003, 0007, 0008
- `docs/designs/2026-11-14-analysis-layer.md`
- `docs/sessions/2026-11-14.md`
- `tools/data-tour/` (fee assumptions, by search)

**Issues:** #10, #12, #14 (with comments; #10 and #12 have none), #13 (1 comment), #37 (no comments), #38, #28, #11, #26, #33, #39.

**Web:** the TradeSkillMaster and Warcraft Tavern pages couldn't be fetched. `support.tradeskillmaster.com` and `www.warcrafttavern.com` would need to be allowed in the session's network settings. So TSM formulas are still unverified.
- [TSM value sources](https://support.tradeskillmaster.com/custom-strings/which-value-sources-can-i-use-and-what-do-they-mean): official for TSM, read only as a search snippet. DBRegionSaleRate is "sells about X% of the time it's posted"; DBRegionSoldPerDay is the average sold per house per day. The formula wasn't found.
- Blizzard hotfixes, 2026-11-10 ([forum](https://us.forums.blizzard.com/en/wow/t/2403040/6)): official. Announced a 1-copper minimum deposit (pulled; due 2026-11-17); quest gold from level 48 up.
- News coverage of the same hotfix: community news. [Icy Veins](https://www.icy-veins.com/wow-forever/news/class-changes-profession-improvements-ah-deposit-gold-buffs-wow-forever-hotfixes-november-10th/), [MassivelyOP](https://massivelyop.com/2026/11/11/wow-forever-reduces-auction-house-listing-costs-and-adds-more-gold-to-high-level-quests/), [Warcraft Tavern](https://www.warcrafttavern.com/forever/news/class-economy-changes-wow-forever-hotfixes-for-november-10/).
- [warcraft.wiki.gg, Neutral Auction House](https://warcraft.wiki.gg/wiki/Neutral_Auction_House): community wiki, about Classic and retail, not Forever. 15% neutral cut; same-account bid limits.
- Profession guides, rated guide-seller or gold-seller: [Boostroom](https://boostroom.com/blog/wow-forever-professions-guide-best-professions-for-leveling-gold-and-endgame), [PlayerAuctions](https://www.playerauctions.com/wow-forever-guide/tips-guides/best-professions-for-gold-making/), [ExpCarry](https://expcarry.com/wow-forever-professions-guide), [Timesaver](https://timesaver.gg/blog/wow-forever-best-professions-to-pick). Gathering is low investment; Alchemy and Enchanting have steady demand; the profession list and balance aren't final.
- From memory, unverified, and turned into hypotheses or checks: retail cheapest-first commodity buying; the Classic deposit formula (vendor price × duration); the Blizzard item API's price and level fields; wago.tools table names; TSM DBMarket's window.

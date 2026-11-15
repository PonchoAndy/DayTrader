# DayTrader — Planning Notes

Status: **planning / research**. No requirements or MVP yet.
Last updated: 2026-11-14 (session 3)

Goal for now: **grab, analyze, and display** WoW Forever auction house data, so we can find
profitable trades. Trading/posting automation is out of scope (and against the game's rules).

**Vision (owner, 2026-11-15):** not just an auction house dashboard but an **economic intelligence
center**. It should explain how the WoW Forever economy behaves and where it is heading (launch
glut, leveling demand, supply shocks, inflation), so a player can take positions with a thesis and
a holding plan, not only flip today's prices. The Economist agent (`.claude/agents/economist.md`,
#66) is the first piece of this.

---

## 1. Can we get the data? — Yes, two ways

### Path A: Blizzard's official Game Data API (recommended starting point)

WoW Forever launched 2026-11-04, and community developers report Blizzard's API has served
Forever data since launch. **Nothing below is from official Blizzard docs yet.** It comes from
an open-source client ([Pinta365/blizzard_api](https://github.com/Pinta365/blizzard_api),
"verified against the live API (EU, US, KR, TW) on 2026-11-06") and forum posts. We need to
confirm it ourselves with our own key.

| What | Value |
|---|---|
| Base URL | `https://{region}.api.blizzard.com` (region = `us`, `eu`, `kr`, `tw`) |
| Auth | OAuth client-credentials token from `https://oauth.battle.net/token` |
| Namespaces | `dynamic-forever-{region}` (auctions), `static-forever-{region}` (items) |
| List auction houses | `GET /data/wow/ruleset/{rulesetId}/auctions/` (**trailing slash required**) |
| One house's auctions | `GET /data/wow/ruleset/{rulesetId}/auctions/{auctionHouseId}` |
| One house's commodities | `GET /data/wow/ruleset/{rulesetId}/auctions/{auctionHouseId}/commodities` |
| Item details | `GET /data/wow/item/{itemId}` (static namespace) |

How the Forever AH is organized (per the forum thread, checked 2026-11-13 — verify):
- No realms. Rulesets replace them: `/data/wow/ruleset/index`. US/EU have 1 PvP, 2 Normal,
  3 Roleplay, 15 Roleplay PvP; KR/TW have 1 and 2.
- Auction data went live **2026-11-06**. Each ruleset lists **15 auction houses** (IDs 110–121
  and 123–125): five each of Alliance, Horde and Blackwater (neutral). Why five of each is
  unknown — open question.
- Houses 112, 115, 118 were empty (no `auctions` field at all — treat it as optional).
- Every ruleset in a region returns the **same** houses and auctions; the ruleset ID must be
  valid but doesn't filter anything. **Don't sum across rulesets** or you'll multiply counts.
- Responses are big: the busiest houses hold 50–68k auctions, **~9 MB per response**. A full
  pull of all houses could be ~50–100 MB. We can't keep every raw hourly pull forever; plan to
  store per-item hourly summaries and keep raw pulls only briefly.
- Auctions: `id, item{id, context, bonus_lists, modifiers}, buyout, bid?, quantity, time_left`.
  Commodities: `id, item, quantity, unit_price, time_left`. The old
  `/data/wow/auctions/commodities` returns 404.
- ~43% of item IDs seen on one EU house returned 404 from the item endpoint. **Solved:** the
  retail item database names most of them (see "Item names" below).
- wowauctionhouse.com says it scans Forever hourly from every house (it also takes
  player-uploaded scans). Assume hourly refresh until we measure it.
- Realm and WoW Token endpoints reportedly 404 for Forever.

**What the API gives us:** a snapshot of every listing (item, quantity, buyout/unit price,
time-left bucket). **What it doesn't:** who posted it, and what actually *sold*. Sales have to
be inferred by diffing snapshots (listing disappeared before its time ran out ≈ probably sold,
or was cancelled — this is noisy).

### First real snapshot (2026-11-14, `collector/probe.py`, PonchoAndy/DayTrader#9)

Verified with our own key, US region, ruleset 2 (Normal). One full pull of all 15 houses
(auctions + commodities):

| | |
|---|---|
| Time to pull everything | **~13 seconds** |
| Size | **85 MB raw JSON, 9.3 MB gzipped** (gzip ≈ 9x) |
| Listings | ~485k auctions + ~448k commodity listings |
| Distinct items | 6,952 across all houses |
| Data age | `Last-Modified` 23:17 UTC when pulled at 00:08 UTC → consistent with an hourly refresh (to confirm by pulling over a day) |

Per house (auctions / commodities):

| Faction | Big houses | Medium houses | Empty house |
|---|---|---|---|
| Alliance | 110 (88k / 82k), 111 (99k / 78k) | 119 (22k / 24k), 123 (21k / 21k) | 112 |
| Horde | 113 (104k / 90k), 114 (99k / 81k) | 120 (17k / 16k), 124 (22k / 24k) | 115 |
| Blackwater | 116 (6k / 13k), 117 (7k / 15k) | 121 (0.4k / 1k), 125 (0.4k / 1.5k) | 118 |

What we learned:
- Each faction has **two big, two medium and one empty** house. The houses within a faction
  carry mostly the same items (house 114 shares 93% of 113's items), so they look like separate
  markets (perhaps separate server groups), not splits of one market. Why there are five is still unknown.
- **Auctions and commodities are separate**: no shared item IDs or listing IDs between the two
  endpoints. Both must be pulled.
- Auction listings: `id, item{id, ...}, buyout, quantity, time_left` (`bid` on only ~0.2%).
  Commodity listings: `id, item{id}, quantity, unit_price, time_left`.
- `time_left` buckets: SHORT / MEDIUM / LONG / VERY_LONG.
- **Item names: only 52.5% of sampled item IDs resolve** (105 of 200; the rest 404). Close to
  the community's 43% failure figure. We need another source for names (see #9 follow-ups).

Implications:
- **Storage:** ~9 MB per hourly pull gzipped ≈ 220 MB/day. Keeping 7 days of raw pulls ≈ 1.6 GB,
  well inside R2's free 10 GB. Summaries will be far smaller.
- **GitHub Actions minutes:** a pull takes seconds, so an hourly run is ~1 minute including
  setup, roughly 720 minutes a month. That fits the **private** repo's 2,000 free minutes, so
  #5 no longer forces a choice between public and every-2-hours.

### First night of hourly data (2026-11-14, `collector/report.py`, PonchoAndy/DayTrader#28)

Read with the workflow's `report` switch (Actions → Collect auctions → Run workflow → tick "report").
Covers 01:00–16:00 UTC on 2026-11-14: 17 runs, 14 snapshots stored, 0 HTTP errors.

- **Blizzard refreshes at :17 every hour, without fail.** Our pull lands a median 44 min later
  (GitHub starts scheduled runs late).
- **We lose an hour when GitHub runs very late.** The 06:27 and 12:27 runs started after the next
  refresh (07:30, 13:19), so snapshots 06:17 and 12:17 are gone for good: Blizzard only serves
  the latest data. 2 of 13 hours missed. Fix options in #28.
- **Update after 24 hours (2026-11-15):** 3 of 24 hours lost (01:17 by 1 minute, 12:17 by 2 minutes,
  06:17 when GitHub was 63 minutes late and then skipped a run). Scheduled runs started 29–63 min
  after the :27 slot (median ~40). A run must start between :18 and :16 of the next hour, so the slot
  moves to **:05**, which fits every delay seen, at no extra cost. A backup slot (+720 minutes a month)
  waits until a few days at :05 show whether hours are still lost (#28).
- **Supply has a daily rhythm.** Listings peaked ~05:00–07:00 UTC (US late evening: ~548k Horde,
  ~521k Alliance) and drained ~30% by 15:00 UTC (~387k / ~377k), as auctions expire or sell
  and fewer people post overnight. Needs a few days to confirm.
- **Prices move a lot hour to hour.** On Horde house 113, of 1,146 commodities listed every hour,
  the cheapest-10% price swung by a median 23% over the 12 hours, and 1 in 10 swung more than
  186%. Many big % moves are on penny items (0.01 g → 0.04 g), so signals need a minimum price.
- **Bought-up supply is visible.** Leveling and crafting materials drained fastest without the
  price moving: Copper/Tin Ore -87–89%, Red Wolf Meat -92%, ammunition -84–96%, Mithril Bar -81%.
  That's the raw material for a sale-rate estimate (#10).
- The goods-value total is still skewed by absurd listings (Alliance jumped to ~1.0M gold);
  the 10M-gold cap per unit is too loose for a real metric.

### Europe and the two-region collector (2026-11-15, PonchoAndy/DayTrader#52, #54, ADR 0009)

- **Europe:** the same 15 house IDs and faction layout as the US, refreshed at ~:18–:19, ~121–127 MB
  per hourly pull (US ~85–106 MB), 112k summary rows. Stored under `eu/` with its own state file.
- **Timing on GitHub's runners:** the time is CPU, not downloads. Parsing, summarizing and gzipping
  ~227 MB one file at a time took 42–53 s, so a two-region job ran 62–73 s (billed 2 minutes).
  Processing on both cores, orjson, gzip level 1 and cached packages brought the job to **~22 s**
  (collect step 14–16 s), so one run covers both regions inside the one-minute billing unit.
- Raw files at gzip level 1 are ~25% bigger (US 11.5 → 14.8 MB an hour).

### Item names (2026-11-14, PonchoAndy/DayTrader#27)

- **Item IDs are permanent** and Forever uses retail WoW's IDs (we saw 25 to 289,560). So names
  are looked up once and cached in `items/items.parquet`.
- Forever's own item database (`static-forever-us`) knows only ~57% of the IDs on its auction
  house. **Retail's database (`static-us`) fills most of the gap.**
- Result on a full snapshot (6,975 IDs): **96.7% of items named** (3,971 from Forever, 2,771 from
  retail), **99.45% of listings**. The 233 unnamed IDs are rare items, about 0.5% of listings,
  retried weekly. Wowhead or wago.tools could fill them if they matter.
- One ID can have many **variants**. In WoW Forever these are the "of the …" suffixes: each
  listing carries at most one bonus ID, and 3,324 auction IDs have them. Prices differ a lot
  (Archer's Cloak: 36 variants, medians 0.3 g to 1 g).
  **Solved (#30):** summaries are keyed by item + `variant` (bonus IDs), and
  `items/bonuses.parquet` names each bonus ID from WoW Forever's own game data (wago.tools, branch
  `wowf`; Blizzard's API has no names for them, and retail/Raidbots data lacks Forever's IDs).
  All 93 bonus IDs seen are named. Hourly summaries grew to ~107k rows / ~1.3 MB
  (~0.9 GB a month), which makes the daily roll-up (#26) and an hourly retention rule more pressing.

### TSM's numbers and WoW Forever's auction rules (2026-11-15, research pass, PonchoAndy/DayTrader#10, #13)

Sources: TSM's own help pages **[official]**, Undermine Exchange's source code (`erorus/shatari`)
**[community-tested]**, Blizzard's Forever hotfix and forum threads (staff posts **[official]**, player
reports otherwise), gold guides **[guide-seller]**. Full links are on #10 and #13.

**How TSM computes its numbers**
- **DBMarket** (per scan): keep the cheapest 15% of units, extend up to 30% until a 20% price jump,
  drop values more than 1.5 standard deviations from the mean, average the rest. Daily values are
  then weighted over 14 days, leaning hard on the last 3 (half-life a little over 2 days; exact
  weights only published as an image). TSM says it reflects what items are *listed* for, not sold for.
- **DBRecent** = the same on the latest scan only; **DBMinBuyout** = lowest listing in the last scan;
  **DBHistorical** = 60-day average of DBMarket; **DBRegionMarketAvg** = average across realms.
- **Sale rate, sold per day and sale average come from players' own sale records** uploaded by the
  TSM desktop app, not from comparing scans (stated for sale average; very likely for the others).
  We can't copy them; we estimate sales from listing flows instead (ADR 0008) and label them estimates.
- No sign that TSM covers WoW Forever. **Undermine Exchange** stores only the lowest price and total
  quantity per item, has no sale-rate numbers, and has Forever commented out in its code.

**WoW Forever auction rules (what's known)**
- **Deposit refund:** returned when the item sells; lost on expiry or cancel. High confidence.
- **Cut:** 5% at Alliance and Horde houses, 15% at Blackwater. Forever's game files (wago.tools
  `AuctionHouse`, branch `wowf`) list these rates for exactly our house IDs (faction 110–115, 119, 120,
  123, 124; Blackwater 116–118, 121, 125) **[datamined]**, unchanged in every client build since
  2026-10-13. One beta sale showed exactly 15%. Client values; one sale at each house confirms (#13).
  The same table confirms which faction each house ID is.
- **Deposit:** vendor sell price × quantity × 5% per 2 hours of duration at faction houses
  (2 h = 5%, 8 h = 20%, 24 h = 60%): one player's figures, matching the game files' 5% rate
  **[guide / forum]**. Returned on sale, lost on expiry or cancel; the minimum applies per listing.
  **Blackwater's deposit rate in the files is 25 (5× the faction houses)**, so probably 25/100/300%:
  unconfirmed. Vendor prices are in wago.tools `ItemSparse.SellPrice` (branch `wowf`, includes Forever's
  vendor-price cuts); we don't collect them yet (#70), and every profit figure needs them.
- **Minimum deposit:** 1 silver per listing as of 2026-11-14 (many player tests, both house types). The
  1-copper change was pulled from the Nov 10 notes; Blizzard (Kaivax, 2026-11-12) says it goes live with
  weekly maintenance on **2026-11-17 (US)** **[official]**, and **2026-11-18 in Europe** (EU staff post,
  quoted by a player). Nothing newer as of 2026-11-15. Blizzard has slipped it once, so check after
  maintenance. Europe a day later gives a natural comparison. Tip from a beta player: compare your money
  before and after posting; the window once showed a copper deposit while 1 silver was taken.
- **Durations:** 2, 8 or 24 hours (Forever client text, same as Classic Era) **[datamined]**. The
  12/24/48 h reports are retail's. The client's time-left labels use retail's limits: SHORT < 30 min,
  MEDIUM 30 min–2 h, LONG 2–12 h, VERY_LONG > 12 h. **So a 2-hour listing is MEDIUM from the start**, and
  `flows.py`'s "vanished in SHORT/MEDIUM = probably expired" undercounts sales (#69).
  Hypotheses to test in our data (Researcher, 2026-11-15, stated before looking):
  - **H-D1** durations are 2/8/24 h: new listings split across MEDIUM / LONG / VERY_LONG with MEDIUM
    well above zero; almost no listing lives over ~25 h.
  - **H-D2** the API's LONG/VERY_LONG boundary is 12 h: 24 h listings turn LONG at ~12 h of age (~16 h
    would mean Classic's 8 h boundary).
  - **H-D3** how big the miscount is: share of new listings first seen as MEDIUM, by house and item kind.
  - **H-D4** the deposit change ships: small lots (`new_lot_lt1s`) jump on US houses from 11-17 and
    Europe from 11-18; no jump by 11-20 means it didn't ship.
  - **H-D5** Blackwater sellers pick 2 h more often (weak; the in-game check is better).
  - **H-D6** maintenance hours: listings returned at maintenance must not count as sales.
- **Sale gold** arrives by mail after 60 minutes for stackable goods (about 2 minutes for gear), a
  change players noticed around Nov 10–11. No evidence that new listings or undercuts appear late on
  the house itself; the delay that matters for us is Blizzard's hourly snapshot at :17.
- **Newest sells first:** among listings at the same price, the most recently posted sells first;
  cheapest price first as usual. Player reports, medium confidence. For sale estimates: the newest
  IDs vanishing first is normal, not cancelling.
- **Gear can't be undercut by copper amounts** (whole silver), per player reports.
- **No posting or cancel limits** documented. Players report automated buy-and-repost (bots).
- **Account "economy holds"** can block the AH for suspected gold buying/selling **[official]**.
- **Vendor prices were cut** on some items (e.g. Mild Spices 1c), which lowers the vendor-price floor.

**What a "house" is (partly answered).** The API's house list has **no ruleset field**, only ID and
name, and every ruleset returns the same 15 houses (checked 2026-11-15). Community sources say each
world has its own Alliance, Horde and Blackwater house. The IDs and sizes fit five such "worlds":
(110, 113, 116) big, (111, 114, 117) big, (112, 115, 118) empty, (119, 120, 121) medium,
(123, 124, 125) medium. Strong hint, not proof; the in-game check in #13 confirms it.

### Path B: In-game addon scan (how Auctionator works)

We looked at Auctionator's source (fork: `sirus-addons/Auctionator`; the official repo
wasn't publicly cloneable from here). How it works:

1. When you open the AH, it calls `C_AuctionHouse.ReplicateItems()` — a "full scan" that
   downloads every listing to your client. Blizzard throttles this (historically once per
   15 minutes).
2. It loops `C_AuctionHouse.GetReplicateItemInfo(i)` to read each listing.
3. It saves prices into a `SavedVariables` table (`AUCTIONATOR_PRICE_DATABASE`). WoW writes
   that to a Lua file on disk (`WTF/Account/<ACCOUNT>/SavedVariables/Auctionator.lua`) when
   you log out or `/reload`.

Key constraint: **addons can't make network calls.** The only way data leaves the game is that
SavedVariables file. That's how TSM, Undermine Exchange uploaders etc. work — a desktop app
watches the file and uploads it.

Path B is useful as a **supplement**: it works when you're logged in, can capture item names
the API is missing, and can record *your own* buys/sales. It's not a good primary source:
it needs you in-game, it's manual, and it's throttled.

**Recommendation:** start with Path A. Add a small addon later (Path B) only if we hit gaps.

---

## 2. "Do I set up the API on make.com?" — No, not needed

make.com / Zapier are for gluing SaaS apps together with small payloads. This job is:
pull several MB of JSON every hour, keep months of history, and run number-crunching on it.
That's a poor fit (and gets expensive on per-operation pricing).

What setup actually looks like:

1. Go to **https://develop.battle.net**, log in with your Battle.net account, and open
   **API Access → Create Client**. Name it "DayTrader"; redirect URL can be
   `http://localhost`. You get a **Client ID** and **Client Secret**. Free.
2. Store those as secrets (never commit them). Locally: a `.env` file in `.gitignore`.
3. A small script (Python is the easy choice) does: get token → list houses → download each
   house's auctions → save to a database. ~100 lines.
4. Run it hourly. Options, cheapest first:
   - Your own PC with a scheduled task (free, but only runs while it's on).
   - **GitHub Actions on a cron schedule** (free for this volume, secrets built in). Good
     first choice.
   - A $5/month VPS or a free-tier cloud function, if we outgrow Actions.
5. Storage: start with **SQLite or Parquet files**; move to Postgres/DuckDB if needed.
6. Display: start with a simple dashboard (Streamlit, or a static web page). Make it nicer later.

---

## 3. How traders actually make money (to research further)

Common strategies from gold-making guides (TSM community, Wowhead economy posts). These are
mostly from people selling guides, so treat claims of profit as unverified.

| Strategy | What the data needs to show |
|---|---|
| **Flipping / sniping** | Listings far below an item's normal price (e.g. < 70% of market value) that you can buy and relist. |
| **Reselling commodities** | Price cycles (time-of-day, day-of-week, patch/reset days) — buy at the dip, sell at the peak. |
| **Crafting for profit** | Material cost (sum of reagent prices) vs. sale price of the crafted item. |
| **Market cornering** | Low-supply items where the total listed quantity is small enough to buy out and repost higher. |
| **New-content speculation** | Forever is brand new — prices are volatile, and early trends matter a lot. |

The standard reference number is TSM's **DBMarket**: a rolling ~14-day weighted average price.
Our core metrics should probably be:

- **Market value** (rolling average of the cheap end of listings, outliers trimmed)
- **Min buyout** now vs. market value (the "deal %")
- **Supply** (total quantity listed, number of sellers' listings)
- **Estimated sale rate** (from snapshot diffs) — this is what separates good flips from traps
- **Volatility** and **time-of-day / day-of-week patterns**
- **Spread between factions / neutral house** (neutral has a higher cut, reportedly 15%)
- AH cut and deposit cost, so profit numbers are real

Research to-dos:
- [ ] Read the TSM docs on how DBMarket / DBRegionSaleRate are computed.
- [ ] Look at how Undermine Exchange and TSM present data (what views traders use daily).
- [ ] Find the Forever-specific economy guides once they mature (game is 9 days old).
- [ ] Confirm AH cut / deposit / listing durations in-game.

---

## 4. Rough architecture (draft)

```
Blizzard API ──hourly──► Collector ──► Raw snapshots (JSON/Parquet)
                                            │
                                            ▼
                                    Analyzer (Python)
                                    - per-item price history
                                    - market value, deal %, supply
                                    - inferred sales
                                            │
                                            ▼
                                    Dashboard (Streamlit/web)
                                    - "deals right now"
                                    - item price charts
                                    - crafting margins

(optional later) In-game addon ──SavedVariables──► importer ──► same DB
```

---

## 5. Decisions made

The full records live in [`docs/adr/`](adr/README.md). Summary:

- **Region: US for trading; Europe also collected** (ADR 0009, #51): same hourly run, US saved first,
  Europe under an `eu/` prefix (summaries 90 days, raw 14 days), to test whether Europe gives an early
  signal for US prices. Korea/Taiwan probed once, decided ~mid-December. (Originally US only, #2.)
- **Ruleset: Normal** first; collect all rulesets if it costs nothing extra. Right now every
  ruleset returns the same houses, so "all rulesets" is the same data as one.
- **Faction: Horde** is the primary market. Collect **Alliance** (and neutral) too. The API
  cost is small (about 30 calls an hour for all 15 houses, far under the limit); the real cost
  is storage and run time, roughly 3x a Horde-only pull, which per-item hourly summaries keep
  manageable. Build everything with faction as a setting, so views can switch factions
  without code changes.
- **Storage: Cloudflare R2** (bucket `daytrader-data`), small overage charges OK. Costs and sizes:
  `docs/SYSTEMS.md`. (ADR 0005, #6)
- **Collector: private repo, Python, GitHub Actions hourly at :05** (moved from :27, #28; Blizzard
  refreshes at ~:17 US, ~:18–:19 Europe). US + Europe in one ~22 s run; each run logs its own health
  (#18). Raw pulls ~15 MB (US) and ~18 MB (Europe) gzipped per hour; summaries ~1.3–1.6 MB. (ADR 0006, 0009)

- **Retention:** raw pulls 7 days (**14 for now**, until #37's raw-data measurements are done, #38);
  **hourly summaries 3 months**, reviewed for usefulness during
  that time (shorten if rarely needed); daily summaries indefinitely. (ADR 0007, #26)
- **Listing flows (accepted part of ADR 0008):** a daily job matches listing IDs hour to hour in
  the raw pulls and saves per-item counts of units posted, vanished early (sold or cancelled),
  vanished near expiry and partly bought. Kept 90 days; it's the basis for sale rate (#10).
  Backfill must run before the first raw pulls expire, so raw retention goes from 7 to 14 days until
  it has. The same job also saves four extra trading measures as hourly counts (#40): the price
  position of what sold, how long listings sat, depth near the cheapest price, and undercuts;
  plus four posting-behaviour measures: lot-size mix of new listings, a rough seller count, expiry
  waves, and "wall" listings.
  Built and running nightly since 2026-11-15 (#37). The rest of the analysis layer (daily roll-up,
  metrics, page export) is proposed.
- **Build-helper agents** (ADR 0010): Architect, Strategist, Designer, Researcher and Data engineer
  in `.claude/agents/`, handing work over through saved documents in `docs/designs/`. Next: Reviewer,
  Scribe, Analyst (#15).

## 6. Open questions for you

Open questions now live as `Decide:` issues, one per question, shown on the Issue Deck (the
"From agents" filter lists the ones the agents raised). Early questions from this section were
answered: it runs on GitHub Actions (ADR 0006), in Python, viewed as web pages for now
(dashboard choice still open, ADR 0005); professions and play style become app settings later.

## 7. Suggested next steps

See the "Suggested next" list in the newest recap in `docs/sessions/`, and the open issues.

---

## Sources

- [Pinta365/blizzard_api](https://github.com/Pinta365/blizzard_api) — open-source client with WoW Forever AH endpoints (`src/wow_forever/auction_house.ts`)
- [Blizzard forum: "WoW: Forever API: what works so far"](https://us.forums.blizzard.com/en/blizzard/t/wow-forever-api-what-works-so-far-plus-a-ts-client/60334)
- [Everloot PR #867 — Forever namespaces](https://github.com/Everloot/everloot/pull/867)
- [sirus-addons/Auctionator](https://github.com/sirus-addons/Auctionator) — Auctionator fork used to read the scanning code
- [TSM public web API](https://support.tradeskillmaster.com/api-documentation/tsm-public-web-api)
- [Undermine Exchange API](https://undermine.exchange/api.html)
- [Method.gg gold-making guide](https://www.method.gg/guides/best-ways-to-make-gold-in-the-war-within)
- [AH sniping overview](https://www.littlestuff.co.uk/?p=41723)
- [Forever AH guide (shared AH)](https://theforeverguides.com/gold-making/auction-house/)
- [WoW Forever AH locations, deposits](https://warcraftmaps.com/guides/auction-house-and-vendors)

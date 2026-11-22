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
**Three phases (ADR 0013):** (1) **playground**, now: Claude chat sessions with our data and agents, for real
decisions and to shape the product; (2) **the app**: runs on its own, a polished data center; (3) **the AH terminal**:
an in-game addon plus an app section for trading at the auction house, which also feeds the app the player's
characters, bags and purchases. Tag each idea with its phase.
**Data we can't fully trust (standing concern, #81):** "sold" is inferred from listings disappearing, so unreposted
cancellations can pass as sales (and 2-hour sales pass as expiries, #69). Any signal built on sales should say when this
noise is likely to be interfering (price wars, heavy relisting, cheap deposits) rather than present the number as fact.
The player's **profile is the account's whole economic pool**: every character that can reach a market, with its
professions, level, gold and bank space (#78). Before strategy work, **check scope first**: fit the plan to what the
player can actually do now (#79). The owner trades on **Horde, Normal ruleset** (**house 114**, confirmed in game 2026-11-21, #13; Blackwater 117 also reachable),
starting with 5g (2026-11-15). Sessions like 2026-11-15 are **prototyping with Claude's tools**; the app itself will
later run outside Claude Code.

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
  **Confirmed in game 2026-11-21 (#13) [owner, in game]:** 1 Greater Healing Potion (item 1710, vendor price 1s 25c) at
  Orgrimmar showed a deposit of **25c for 8 h and 75c for 24 h**, exactly 20% / 60%. **Blackwater confirmed the same day:**
  the same potion at Booty Bay showed **3s 75c for 24 h** = 300% of vendor price, exactly 5× the faction houses, so
  **25% per 2 h at Blackwater (25 / 100 / 300% for 2 / 8 / 24 h)**.
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
  - **Results (2026-11-16, Data engineer, #69; US, live pulls 01:17–04:17 UTC):** **H-D1 holds so far:**
    of ~501k new listings (first seen 02:17 and 03:17), 11.7% were first seen MEDIUM (17% of units), 69% LONG,
    19% VERY_LONG, none SHORT;
    only 60 of 29,243 first-seen-MEDIUM listings were still up 2 h later (0.2%, all showing SHORT: probably
    expired listings the API hadn't cleared yet). "Almost none over ~25 h" needs a day of data: the nightly
    flows log's `overlived` count now checks it. **H-D3:** MEDIUM share of new listings 11.6% for both
    commodities and gear; by house 3–14% (faction houses 110/111/113/114 11–14%, Blackwater and 119/120/124
    3–13%). **Miscount:** 107k–214k units an hour that the old rule called expired were 2-hour listings
    vanishing early (+10–19% early units; hour-sum sold estimate +16% at 03:17), mostly ammunition by units
    (Razor Arrow, Solid Shot, Sharp Arrow), then cloth, bars and leather. Fixed in `flows.py` (#69).
  - **Cancel check (#81, 2026-11-16):** commodity buyers get the cheapest units first: 99.9% of partly bought
    units (certain sales) were at the cheapest surviving price. So a commodity listing that vanished while a
    cheaper one stayed up all hour was not bought ("skipped"): 14–19% of commodity early units an hour,
    mostly priced well above the cheapest (already outside the sold estimate); 4–5% of the "cheap" early
    units that sold estimates count. `flows.py` now flags these and burst-posted batches pulled down whole.
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

**What a "house" is (answered, 2026-11-15, Researcher, `docs/designs/2026-11-15-which-house.md`).** Each house is one
faction's market on one **ruleset**. Blizzard announced five rulesets: Normal, PvP, Roleplay, Roleplay PvP, and Hardcore
(after launch) **[official]**. Forever's game files (wago.tools `AuctionHouseRedirect` + `AvailableSuperDistrict`, branch
`wowf`, build 1.60.1.70938) send each ruleset to its own houses **[datamined]**:

| Ruleset (API id) | Alliance | Horde | Blackwater |
|---|---|---|---|
| PvP (1) | 110 | 113 | 116 |
| Normal (2) | 111 | **114** | 117 |
| Roleplay (3) | 119 | 120 | 121 |
| Roleplay PvP (15) | 123 | 124 | 125 |
| Hardcore (4, not open; API 404) | 112 | 115 | 118 |

This explains "five per faction" and the always-empty houses. The API can't show it: any ruleset ID returns all 15 houses,
and houses have no ruleset field (re-checked 2026-11-15). **Take the ruleset from the house ID, never from the query.**
Mail between rulesets is blocked ("You can't send mail to that ruleset", client text) and characters can't change ruleset
(Blizzard; dead Hardcore characters excepted). Factions on the same ruleset meet only at their shared Blackwater house. An
unplaced "Auction House" (ID 122, new in Forever) has Blackwater's settings in the files (FactionID 369, which the files
name "Gadgetzan", the Steamwheedle faction that Blackwater houses belong to; deposit rate 25, **15% cut** [datamined, build
70938]), yet the redirect table points each faction to its own ruleset market; where it is in the world is unknown. Matches wowauctionhouse.com's labels. Confirmed in game on 2026-11-21 by matching the owner's order book (#13, below). Note: earlier docs and
mock-ups treat **113 (PvP Horde)** as the owner's house; they need switching to 114.

**Durations confirmed (2026-11-15, Researcher, #13) [our data]:** of 213k listings under 1 h old, 12% showed MEDIUM (30 min–2 h
left), so a 2-hour option exists; none showed SHORT. Listing lengths are 2/8/24 h, not retail's 12/24/48 (a 48 h option isn't
ruled out yet: a listing living over ~25 h would show it). Cut and deposit rates in the files (build 70938): faction houses
5% cut, deposit rate 5; Blackwater 15% cut, deposit rate 25. **#13 status:** only the marker listing (house 114), one
sale-mail cut and one Blackwater deposit still need the owner, none time-limited; the pre-maintenance 1-silver deposit is
already confirmed by many player tests. **Update 2026-11-21:** the home house (114) and the faction-house deposit rate are
confirmed in game (below and above); the 1-silver minimum is gone (a 25c deposit showed). Still open: Blackwater's deposit and
cut, and the cut on a sale mail. **Later the same day:** Blackwater's deposit confirmed (5× faction, see above) and Booty
Bay identified as **house 117** (its potion order book matched 117's listings: 4s 64c ×11, 5s 00c ×3, 8s 00c ×2 exactly).
Only the sale-mail cuts (5% faction, 15% Blackwater) are still unchecked.

**Home house confirmed (2026-11-21, #13) [owner, in game + API]:** the Greater Healing Potion order book on the owner's
Orgrimmar auction house (399 units, e.g. 3s 87c ×206, 3s 89c ×26, 3s 90c ×26) matched house 114's listings in the API
(snapshot 03:25 UTC): **347 of the 399 units at the same prices**, against 0 on houses 113, 120 and 124 and 3–7 on
Blackwater 116/117 (chance overlaps). The rest were listings posted or bought after the snapshot. So the owner's market is
**house 114 (US, Normal, Horde)**, as the game files said (ADR 0012).

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

### Leveling-material speculation (2026-11-15, Researcher, `docs/designs/2026-11-15-leveling-materials-research.md`)

**Forever's shape [official]:** level 60 since launch (2026-11-04), no level-capped phases; raids open 2026-12-09;
Hardcore "sometime after launch", fully enclosed (characters can transfer out, not in). 600+ new recipes; Legacy system
rewards leveling alts.

**Scarce materials** (Forever only) come in three tiers [datamined]: item level 25 Pyrite / Frilled Lichen / Pristine Leather,
45 Rosecap / Pristine Hide, 60 Stranglevine / Pristine Scale. Beta testers (Oct 2026) and one live player (11-08) report
**tier 1 can only be gathered by characters level 25 or lower** [guide / forum]; untested for Pyrite. Bountiful Harvest raises
the scarce-drop chance.

**Black Market (Researcher, 2026-11-21, #13).** In **Powderfuse Port** (Riverglades, ~78, 52), a neutral Steamwheedle town with
its own faction "Powderfuse" (2827) [datamined]. Two NPCs [guide / forum, beta 2026-09-19 to 10-04]:
- **Mister Graphed:** a fixed-price vendor.
- **Madam Swyndle:** a retail-style Black Market Auction House. Bid-only, no player listings, gear and collectibles.

Graphed's beta list:

| Price | Items |
|---|---|
| **5g** | Pyrite, Frilled Lichen, Pristine Leather |
| **20g** | Bauxite, Rosecap, Pristine Hide |
| **50g** | Pitchblende, Stranglevine, Pristine Scale, Fel Crystal, Torbernite, Death Lotus, Black Lotus, Arcane Crystal |
| 150g | Gift of Galloping |

Stock was "no limit" in beta [guide / forum, beta].
- **Pitchblende is the tier-3 mining material** (item level 60, like Stranglevine and Pristine Scale) [datamined].
- The Legacy perk **Bartering** takes 10% off all vendor gold prices [datamined].
- **Live status:** players treat it as a live 50g cap (11-17/18). There is no live price list and no official note yet
  [guide / forum, live]. The material prices are set on the server, so they can't be datamined.
- **Not related to Blackwater:** the Black Market is not one of our 15 houses (see the faction note above).
- **For trading:** it's only a ceiling. Tiers 1–2 trade hundreds of times below it today. It matters for Black Lotus, Arcane
  Crystal and the new level-60 materials.
- **Owner check (optional):** visit Mister Graphed and note his prices and any stock count.
- On 2026-11-21 the owner dropped the Black Market price from the Stockpile Ticker. The name read like the Blackwater auction
  house, and the price was far above today's market.

**Recipes [datamined, build 1.60.1.70938]:** new "variant families" (same item, 5–6 versions, each with a different gem or
flavour reagent), so classic gems substitute for each other. Forever's high-level smithing and leatherworking (skill 200–290)
needs tier-1 scarce materials in every version (Sulfuric Acid = 2 Pyrite; Pristine Leather). New necklace enchants
(skill 225–265) take 4 Sulfuric Acid, Pyrite or Cerulean Dye. Runecloth Bag now also needs 2 Cerulean Dye + 4 Magenta Dye.
Enchanting needs about half Era's dust and essence. No Jewelcrafting. Gem and material vendor prices equal Classic Era's.

**First read [our data, one hour, 2026-11-15]:** every classic gem sits within ~0–20% of vendor price on the big houses
(Malachite 15c, Tigerseye ~1s, Lesser Moonstone 6s), so buying at that price is risk-free apart from gold tied up and bag
space (stacks of 20). Ores trade 4–40× vendor. Pyrite is also at vendor (1s); Frilled Lichen ~20–30s, Cerulean Dye ~45–65s.
**Thesis ranking:** strong for Pyrite, Pristine Leather, Frilled Lichen; medium for Tigerseye, Shadowgem, Jade, pearls;
weak for Malachite, Lesser Moonstone, Strange Dust. Tests: H-L1 to H-L8 in the report. Gem drop rates in Forever are
unknown (~1% per node in TBC data, snippet only). House map: see §1 "What a house is" (Normal Horde = 114, PvP Horde = 113).

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
- **Three phases of use** (ADR 0013): playground (now), the app, the AH terminal (addon).
- **Trading day:** 12:00–12:00 UTC (7am Eastern in winter; ADR 0014, #44), named by its start date.
- **Home house: 114** (US, Normal, Horde; ADR 0012, #85). Reachable: 114 and Blackwater 117. A row's ruleset
  comes from its house ID (map in §1), never from the API query.
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
- **Economist agent** (2026-11-15, #66): studies how the economy behaves and where it's heading; first job was
  the launch-glut outlook (`docs/designs/2026-11-15-economist-launch-glut-outlook.md`).
- **Money** (ADR 0011, #61): stored and computed as whole copper; shown everywhere as **gold with 4 decimals**
  (1g 1s 1c = 1.0101), copper digits set apart visually. Tables keep 4 decimals; prose may round 100g+; amounts under
  a copper per unit are shown per trade.
- **Stockpile Ticker live** (ADR 0015, #99): numbers refresh hourly (an export at the end of the collect job, copied
  into the page's database by an hourly Claude task at :15); the Analyst writes a briefing per holding every 6 hours
  and on a 30% price move.
- **Claude reads R2 directly** (ADR 0016, 2026-11-22): a read-only Cloudflare API token (Workers R2 Storage:
  Read) is a network secret on the DayTrader cloud environment; `tools/r2read.py` lists and downloads any
  stored file. The Analyst now sees every item, hour and house, not just the committed exports.

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

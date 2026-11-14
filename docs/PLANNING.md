# DayTrader — Planning Notes

Status: **planning / research**. No requirements or MVP yet.
Last updated: 2026-11-14

Goal for now: **grab, analyze, and display** WoW Forever auction house data, so we can find
profitable trades. Trading/posting automation is out of scope (and against the game's rules).

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
- ~43% of item IDs seen on one EU house returned 404 from the item endpoint. We'll need a
  fallback for item names/metadata (e.g. scrape from in-game via addon, or Wowhead-style DBs).
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

- **Region: US only** (no EU). API host `us.api.blizzard.com`. — PonchoAndy/DayTrader#2
- **Ruleset: Normal** first; collect all rulesets if it costs nothing extra. Right now every
  ruleset returns the same houses, so "all rulesets" is the same data as one.
- **Faction: Horde** is the primary market. Collect **Alliance** (and neutral) too. The API
  cost is small (about 30 calls an hour for all 15 houses, far under the limit); the real cost
  is storage and run time, roughly 3x a Horde-only pull, which per-item hourly summaries keep
  manageable. Build everything with faction as a setting, so views can switch factions
  without code changes.
- **Storage: Cloudflare R2** (bucket `daytrader-data`), small overage charges OK. Raw pulls
  kept ~7 days; hourly summaries a few months; daily summaries indefinitely. (ADR 0005, #6)

## 6. Open questions for you

1. **Where should it run?** Your PC, GitHub Actions, or a cheap cloud server?
2. **How do you want to view it?** Web dashboard, spreadsheet, Discord alerts, phone?
3. **Your professions / play style?** Crafting margins only matter for what you can craft.
4. **Language comfort?** Python is the suggestion; tell us if you'd prefer something else.

## 7. Suggested next steps

1. You: create a Battle.net API client (step 2.1 above) and keep the ID/secret handy.
2. Us: write a tiny "probe" script that hits the endpoints above, confirms they work, and
   saves one snapshot so we can look at real data.
3. Run it for a few days to measure refresh rate and data size.
4. Then write real requirements and pick an MVP.

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

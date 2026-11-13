# DayTrader — Planning Notes

Status: **planning / research**. No requirements or MVP yet.
Last updated: 2026-11-13

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

How the Forever AH is organized (per community reports — verify):
- No realms. Auctions are grouped by **ruleset** and **region**, with Alliance, Horde and a
  neutral (Blackwater) house.
- Right now every ruleset in a region returns the **same** houses and auctions; the ruleset ID
  must be valid but doesn't filter anything.
- Responses are big (tens of thousands of auctions, several MB).
- ~43% of item IDs seen on one EU house returned 404 from the item endpoint. We'll need a
  fallback for item names/metadata (e.g. scrape from in-game via addon, or Wowhead-style DBs).
- Retail's AH API refreshes roughly **hourly**. Assume the same until we measure it.
- Realm and WoW Token endpoints reportedly 404 for Forever.

**What the API gives us:** a snapshot of every listing (item, quantity, buyout/unit price,
time-left bucket). **What it doesn't:** who posted it, and what actually *sold*. Sales have to
be inferred by diffing snapshots (listing disappeared before its time ran out ≈ probably sold,
or was cancelled — this is noisy).

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

## 5. Open questions for you

1. **Region and faction?** (US/EU? Alliance/Horde?) — decides which house we track first.
2. **Where should it run?** Your PC, GitHub Actions, or a cheap cloud server?
3. **How do you want to view it?** Web dashboard, spreadsheet, Discord alerts, phone?
4. **Your professions / play style?** Crafting margins only matter for what you can craft.
5. **Language comfort?** Python is the suggestion; tell us if you'd prefer something else.

## 6. Suggested next steps

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

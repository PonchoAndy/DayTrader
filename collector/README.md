# Collector

- `collect.py`: the hourly collector. GitHub Actions runs it at :05 past each hour (moved from :27 on 2026-11-15, #28), with a backup run at :35 (ADR 0017)
  (`.github/workflows/collect.yml`), writing to the Cloudflare R2 bucket `daytrader-data`.
- `probe.py`: one-off exploration: pulls a snapshot and reports sizes, houses and item-name coverage.
- `blizzard.py`: shared API client.
- `bonuses.py`: variant names (bonus ID → "of the Eagle"), from WoW Forever's game data on wago.tools.
- `market.py`: the `market` switch's export of crafting-material prices for Claude sessions (below).
- `pulse.py`: the Analyst's daily export: every hour of the watchlist and whole-market totals (below, #19).
- `../tools/r2read.py`: read-only access to the bucket from Claude cloud sessions (`ls`, `get`, `sync`, `read_parquet`), through a read-only Cloudflare API token held by the environment (ADR 0016).
- `vendor.py`: vendor prices for every item, from the game's data files on wago.tools, refreshed weekly (#70).
- `items.py`: item names. IDs are permanent, so each is looked up once: WoW Forever's item database first, then retail WoW's (same IDs; Forever's own database is incomplete). Unknown IDs are retried weekly.

## What's in the bucket

| Path | What | Kept |
|---|---|---|
| `raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<auctions\|commodities>.json.gz` | Blizzard's responses, gzipped (~10 MB per snapshot) | 14 days for now (R2 rule `expire-raw-pulls-7d`, set to 14 until the #37 backfill has run; then back to 7) |
| `hourly/<YYYY-MM-DD>/<snapshot>.parquet` | One row per house × kind × item × **variant**: listings, quantity, min / p10 / p25 / median / max unit price (copper). `variant` = the listing's bonus IDs joined with `:` (`""` = no variant; always `""` for commodities). Files before 2026-11-14 ~04:00 UTC have no `variant` column (variants merged). | 90 days (R2 rule `expire-hourly-summaries-90d`; ADR 0007) |
| `items/items.parquet` | Item names: `item_id, name, quality, item_class, item_subclass, inventory_type, source, checked_at`. `source` = `forever` / `retail` / `missing`. Join it to the summaries on `item_id`. | indefinitely (~0.3 MB) |
| `items/vendor.parquet` | Vendor prices (#70): `item_id, sell_price` (what a vendor pays you), `buy_price` (for `buy_qty` units; set for nearly every item, so it does **not** mean a vendor sells it), `source` (`forever` = Forever's game files on wago.tools, branch `wowf`; `classic_era` = Classic Era's, for items missing from Forever's), `fetched_at`. Copper. Refreshed weekly by the hourly collector (`vendor.py`). ~300 seen items are in neither: unknown, not 0. | replaced weekly (~0.2 MB) |
| `items/bonuses.parquet` | Variant names: `bonus_id, suffix, stats, source_build, fetched_at`, e.g. 12718 → "of the Eagle", "Intellect + Stamina". From WoW Forever's game data on wago.tools (branch `wowf`), refreshed weekly. | replaced weekly |
| `flows/<YYYY-MM>/<day>.parquet` (and `eu/flows/`) | Listing flows per hour from matching listing IDs in `raw/` (`flows.py`, #37, ADR 0008): posted, vanished by time-left, early (sold or cancelled) vs. expired, partly bought, price position and age of early vanishings, undercuts, lot-value mix, depth, crowding at the cheapest, walls, time-left mix, and a cancel check (`suspect_cancel_units`, `suspect_cheap_units`, `cancel_flag`, #81). Columns are listed at the top of `flows.py`. **Meaning change (#69):** "early" is judged from the listing's duration (2/8/24 h, from its first time-left bucket) in files built by the 2026-11-16 code, which have an `early_units` column; older files used "vanished with 2+ h left", which counted 2-hour listings' sales as expiries. `early_at_min`…`early_above`, `early_value`, `age_*` and `relist_guess_units` follow whichever rule built the file; `gone_*_units` (by last time-left bucket) never changed. Built daily at 01:35 UTC; catches up on missed days. `state/first_seen.parquet` carries per listing `first_seen`, `posted_after` (the snapshot before it), `first_tl` (first time-left bucket) and `burst` across days. The workflow's **flows_rebuild** switch redoes every day still in `raw/` with the current rules. | 90 days (R2 rule `expire-flows-90d`) |
| `flows-hourly/<day>/<snapshot>.parquet`, `state/hourly/` (US) | **Sales every hour (#104), parallel run from 2026-11-20:** the same flows, one hour at a time, computed by the hourly collect job right after collecting (`flows.py --hourly`, only when it can finish within 45 s of the job start; otherwise the next run or the nightly job catches up). Same columns and the same numbers as the nightly file: no rule looks ahead (checked on a replay, row for row). Its own state while it runs alongside the nightly job: `state/hourly/meta.json` (last snapshot done), `first_seen.parquet`, `hist.parquet` (burst baseline), `tail.parquet` (last snapshot's listings). Each night the flows job (`--catch-up`) compares every day it built with these files (`Hourly vs nightly` in its log, `hourly_check` in `runs/flows/`), then brings the hourly state up to date. Run logs: `runs/flows-hourly/`. | until the switch-over (#104 step 3) |
| `runs/<YYYY-MM-DD>/<HHMMSS>.json` | Log of each run: result, sizes, timings (`seconds`, `job_seconds`), errors, and a `health` record (below) | indefinitely (tiny) |
| `state/latest.json` | Last stored snapshot, each house's Last-Modified (used to skip runs with no new data) and, from 2026-11-15, `listings` per `<house>-<kind>` (priced listings, for the health check) | — |

`<snapshot>` is Blizzard's newest Last-Modified time across houses (`YYYYMMDDTHHMMZ`).
Percentiles are quantity-weighted: p10 is the unit price at which the cheapest 10% of units are listed.
Auction prices are buyout ÷ quantity; bid-only auctions (~0.2%) are skipped. Items are keyed by
`item_id` + `variant`; to name a variant, split `variant` on `:` and look each bonus ID up in
`items/bonuses.parquet` (in WoW Forever each listing has at most one bonus ID, the "of the …" suffix).

## Run health (#18, #54)

Every run log (`runs/` and `eu/runs/`, from 2026-11-15) has a `health` record. A health problem
is a flag, never an error: it doesn't fail the run or change the exit code.

| Field | Meaning |
|---|---|
| `ok` | `true` when there are no flags (`null` if the check itself broke; see `error`) |
| `flags` | Plain-text problems, e.g. `2 hour(s) missed since 20261115T0117Z`, `skipped: not downloaded by the 120 s deadline` |
| `refresh_minute` | Minute past the hour of Blizzard's newest Last-Modified (normally :17 US, :18–:19 Europe). Flagged when it moves 3+ minutes from the previous snapshot's |
| `lag_minutes` | Minutes from that refresh to the start of our run. A "no new data" run is flagged when this is over 90 |
| `gap_hours` | Stored runs: hours since the previous stored snapshot (normally ~1.0; over 1.5 is flagged) |
| `missed_hours` | Stored runs: UTC hours (`YYYY-MM-DDTHH`) with no snapshot between the previous one and this one |
| `houses_flagged` | `[{house: "113-auctions", listings, previous, reason}]`: a house that had at least 200 priced listings last time and now has under 25% of them (`empty`, `shrunk`) or failed to download. Always-empty houses (112/115/118) never qualify |

Deadline and failed runs carry only `ok: false` and a flag. Older run logs have no `health`.

**Reading health without R2:** run the workflow with the **health** switch from a branch. It writes
the last 48 hours per region to `tools/health/health.json` and commits it to that branch (from
`main` it only prints to the log). Per region: counts of stored / no-new-data / deadline / failed
runs, `hours_missed` (from the stored snapshots themselves, so it also covers runs from before the
`health` record), `hours_since_last_snapshot`, `houses_flagged`, other flags, refresh minutes seen,
and `job_seconds` median / max / runs over 55 s and 60 s. The `report` switch prints the same
summary in a "Health" section. Locally: `python collector/report.py --local data/store --health-json /tmp/health.json`.

## Crafting-material prices without R2 (`market` switch)

Run the workflow with the **market** switch from a branch (Actions → Collect auctions → Run workflow →
pick the branch → tick **market**). `collector/market.py` reads every stored hourly summary for the US
and Europe, the listing flows and `items/items.parquet`, and commits `tools/market/market.json` to that
branch (from `main` it only writes it on the runner). Read-only on R2.

- **Items:** item class Trade Goods or Reagent (also retail's names Tradeskill / Gem), plus
  Miscellaneous / Reagent (spell reagents): ~430 items. In WoW Forever gems such as Malachite (774) are
  Trade Goods / Other, and nearly all of these trade as commodities; a few (rods, oils) are auctions,
  which are included (`kind`). Per item: `name, quality, class, subclass, kind` and the vendor prices
  `vendor_sell` (what a vendor pays you), `vendor_buy` for `vendor_buy_qty` units, in copper, from
  Blizzard's `static-forever-us` item endpoint. They include Forever's own vendor-price changes, and
  they match wago.tools' `wowf` ItemSparse. They're copied from the previous export, so only new items
  are looked up.
- **Prices**, per region → house (`houses` gives the faction) → item: four arrays aligned with that
  region's `snapshots`: min, p25, median unit price (copper, `null` = not listed) and quantity listed.
- **Flows**, per region → house → item: one array per `flow_fields` entry, aligned with `flow_days`
  (`flow_hours` = hours covered that day). Units per day: `partial` (certain sales), `early_cheap`
  (vanished early, within 5% of the cheapest), `early` (all early vanishings: sold or cancelled),
  `gone_short_medium` (vanished while showing under 2 h left), `relist`, `new`, and
  `sold_est = partial + early_cheap - relist`. Then (added 2026-11-16): `expired` (vanished when it could
  have expired), `early_short_medium` (early units the old rule called expired: the #69 correction),
  `suspect` (early_cheap units that look like cancels, #81), `sold_clean = sold_est - suspect`, and
  `cancel_flag` (1 when `suspect` is at least a quarter of `partial + early_cheap`). "Early" means
  vanished before the listing could have expired, judged from its 2/8/24 h duration, in flows built from
  2026-11-16; older days used "vanished with 2+ h left", which counted 2-hour listings' sales as expired
  (for those days `expired` = `gone_short_medium` and the new fields are 0). `sold_est` stays a low
  estimate: a sale in a listing's last hour still looks like expiry.
- **Size:** ~73 KB per region per hour kept. Over 8 MB (`--max-mb`), the newest 72/48/24 hours stay
  hourly and older hours are thinned to every 3rd/6th/12th/24th UTC hour; as a last step, series
  averaging under 10, then 25, listings an hour are dropped. `sampling` in the file says what was used.

Locally: `python collector/market.py --local data/store --out /tmp/market.json`.

## Every hour for the Analyst (`pulse`, daily, #19)

`collector/pulse.py` writes `tools/analyst/pulse.json`: **every** stored hour since 2026-11-14 (never
thinned, unlike `market`), US only by default. It runs daily at 12:00 UTC (lands ~12:30–13:05 because
GitHub starts late, #28), after the trading day closes (ADR 0014), and with the **pulse** switch.
- **Where it goes:** runs from `main` (the schedule, or the switch on `main`) commit to the data-only
  branch **`analyst-data`**, which holds just this file; a switch run from another branch commits to that branch.
  A session reads it with
  `git fetch --depth 1 origin analyst-data && git show FETCH_HEAD:tools/analyst/pulse.json > /tmp/pulse.json`.
- **What:** per watchlist house × item (`tools/analyst/watchlist.json`, editable: seed is 19 materials on
  houses 114 and 113): hourly `min, p10, p25, median` (copper per unit), `quantity`, `listings`, and the
  hour's flows `posted, sold_est, sold_clean, expired, suspect, cancel_flag` (meanings as in `market`,
  summed over the hour instead of the day). Per house of the region (whole market, all items incl.
  gear): `listings, units, posted, sold_est, sold_clean, value_est, value_clean` (value in copper:
  the bought-out part at its own price, the rest at the previous hour's cheapest).
- **Shape:** `regions.us.hours` lists every snapshot (UTC, `YYYY-MM-DDTHH:MMZ`); each series is an array
  in the same order. `trading_day` names each hour's trading day; `flow_hours` = hours since the
  previous snapshot (2+ after a missed hour), null where flows aren't built yet. Flows are built nightly
  at ~01:35 UTC per UTC day, so at 12:30 the newest ~12 hours (00:00–12:00 UTC) have flow fields null;
  they fill in the next day. Field docs are in `notes` and at the top of `pulse.py`.
- **null ≠ 0:** null = not known (house missing from that snapshot, item not listed for prices, flows
  not built yet). A missing hour is simply absent from `hours`.
- **Cost:** scheduled runs reuse yesterday's file and re-read only the last 3 days (`--prev`,
  `--recent-days`); the switch rebuilds everything. A changed watchlist or field list also rebuilds
  everything. If no hourly file can be read the run fails and the old file stays.
- **Size:** ~50 KB a day with the seed watchlist (~0.35 MB now, ~1.6 MB at 30 days, ~4.7 MB at 90).
  Europe (`PULSE_REGIONS: us,eu` in the workflow) would add ~1 KB per house per day of totals, no flows yet (#56).

Locally: `python collector/pulse.py --local data/store --out /tmp/pulse.json [--prev old.json]`.

## Other regions (ADR 0009)

Europe (and any later region) uses the same layout under its own prefix: `eu/raw/`, `eu/hourly/`,
`eu/runs/`, `eu/state/latest.json` (R2 rules `eu-expire-raw-14d`, `eu-expire-hourly-90d`). US paths
have no prefix. House IDs are the same numbers in every region, so never mix regions in one path,
state file or table; summary rows carry `region`. Item and variant names (`items/`) are shared and
looked up through the US API. `python collector/collect.py --region eu` collects Europe;
`collector/report.py --region eu` reports on it.

## Running it yourself

```bash
pip install -r requirements.txt
python collector/collect.py --local data/store      # writes to a local folder instead of R2
python collector/collect.py --region eu --local data/store --skip-names   # Europe, no name lookups
```

Needs `BLIZZARD_CLIENT_ID` / `BLIZZARD_CLIENT_SECRET` in the environment (not needed in Claude's
cloud sessions, where the proxy supplies the key).

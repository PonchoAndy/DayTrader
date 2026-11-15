# Collector

- `collect.py`: the hourly collector. GitHub Actions runs it at :05 past each hour (moved from :27 on 2026-11-15, #28)
  (`.github/workflows/collect.yml`), writing to the Cloudflare R2 bucket `daytrader-data`.
- `probe.py`: one-off exploration: pulls a snapshot and reports sizes, houses and item-name coverage.
- `blizzard.py`: shared API client.
- `bonuses.py`: variant names (bonus ID → "of the Eagle"), from WoW Forever's game data on wago.tools.
- `market.py`: the `market` switch's export of crafting-material prices for Claude sessions (below).
- `items.py`: item names. IDs are permanent, so each is looked up once: WoW Forever's item database first, then retail WoW's (same IDs; Forever's own database is incomplete). Unknown IDs are retried weekly.

## What's in the bucket

| Path | What | Kept |
|---|---|---|
| `raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<auctions\|commodities>.json.gz` | Blizzard's responses, gzipped (~10 MB per snapshot) | 14 days for now (R2 rule `expire-raw-pulls-7d`, set to 14 until the #37 backfill has run; then back to 7) |
| `hourly/<YYYY-MM-DD>/<snapshot>.parquet` | One row per house × kind × item × **variant**: listings, quantity, min / p10 / p25 / median / max unit price (copper). `variant` = the listing's bonus IDs joined with `:` (`""` = no variant; always `""` for commodities). Files before 2026-11-14 ~04:00 UTC have no `variant` column (variants merged). | 90 days (R2 rule `expire-hourly-summaries-90d`; ADR 0007) |
| `items/items.parquet` | Item names: `item_id, name, quality, item_class, item_subclass, inventory_type, source, checked_at`. `source` = `forever` / `retail` / `missing`. Join it to the summaries on `item_id`. | indefinitely (~0.3 MB) |
| `items/bonuses.parquet` | Variant names: `bonus_id, suffix, stats, source_build, fetched_at`, e.g. 12718 → "of the Eagle", "Intellect + Stamina". From WoW Forever's game data on wago.tools (branch `wowf`), refreshed weekly. | replaced weekly |
| `flows/<YYYY-MM>/<day>.parquet` (and `eu/flows/`) | Listing flows per hour from matching listing IDs in `raw/` (`flows.py`, #37, ADR 0008): posted, vanished by time-left, partly bought, price position and age of early vanishings, undercuts, lot-value mix, depth, crowding at the cheapest, walls, time-left mix. Columns are listed at the top of `flows.py`. Built daily at 01:35 UTC; catches up on missed days. `state/first_seen.parquet` carries listing start times across days. | 90 days (R2 rule `expire-flows-90d`) |
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
  (vanished with 2+ h left within 5% of the cheapest), `early` (all vanished with 2+ h left: sold or
  cancelled), `gone_short_medium` (vanished in the last 2 h: expired, or bought), `relist`, `new`, and
  `sold_est = partial + early_cheap - relist`. `sold_est` is a low estimate: a 2-hour listing shows
  MEDIUM from the start, so its sales land in `gone_short_medium` (#69).
- **Size:** ~73 KB per region per hour kept. Over 8 MB (`--max-mb`), the newest 72/48/24 hours stay
  hourly and older hours are thinned to every 3rd/6th/12th/24th UTC hour; as a last step, series
  averaging under 10, then 25, listings an hour are dropped. `sampling` in the file says what was used.

Locally: `python collector/market.py --local data/store --out /tmp/market.json`.

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

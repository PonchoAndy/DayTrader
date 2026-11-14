# Collector

- `collect.py`: the hourly collector. GitHub Actions runs it at :27 past each hour
  (`.github/workflows/collect.yml`), writing to the Cloudflare R2 bucket `daytrader-data`.
- `probe.py`: one-off exploration: pulls a snapshot and reports sizes, houses and item-name coverage.
- `blizzard.py`: shared API client.
- `bonuses.py`: variant names (bonus ID → "of the Eagle"), from WoW Forever's game data on wago.tools.
- `items.py`: item names. IDs are permanent, so each is looked up once: WoW Forever's item database first, then retail WoW's (same IDs; Forever's own database is incomplete). Unknown IDs are retried weekly.

## What's in the bucket

| Path | What | Kept |
|---|---|---|
| `raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<auctions\|commodities>.json.gz` | Blizzard's responses, gzipped (~10 MB per snapshot) | 7 days (R2 rule `expire-raw-pulls-7d`) |
| `hourly/<YYYY-MM-DD>/<snapshot>.parquet` | One row per house × kind × item × **variant**: listings, quantity, min / p10 / p25 / median / max unit price (copper). `variant` = the listing's bonus IDs joined with `:` (`""` = no variant; always `""` for commodities). Files before 2026-11-14 ~04:00 UTC have no `variant` column (variants merged). | 90 days (R2 rule `expire-hourly-summaries-90d`; ADR 0007) |
| `items/items.parquet` | Item names: `item_id, name, quality, item_class, item_subclass, inventory_type, source, checked_at`. `source` = `forever` / `retail` / `missing`. Join it to the summaries on `item_id`. | indefinitely (~0.3 MB) |
| `items/bonuses.parquet` | Variant names: `bonus_id, suffix, stats, source_build, fetched_at`, e.g. 12718 → "of the Eagle", "Intellect + Stamina". From WoW Forever's game data on wago.tools (branch `wowf`), refreshed weekly. | replaced weekly |
| `runs/<YYYY-MM-DD>/<HHMMSS>.json` | Log of each run: result, sizes, timings, errors | indefinitely (tiny) |
| `state/latest.json` | Last stored snapshot and each house's Last-Modified, used to skip runs with no new data | — |

`<snapshot>` is Blizzard's newest Last-Modified time across houses (`YYYYMMDDTHHMMZ`).
Percentiles are quantity-weighted: p10 is the unit price at which the cheapest 10% of units are listed.
Auction prices are buyout ÷ quantity; bid-only auctions (~0.2%) are skipped. Items are keyed by
`item_id` + `variant`; to name a variant, split `variant` on `:` and look each bonus ID up in
`items/bonuses.parquet` (in WoW Forever each listing has at most one bonus ID, the "of the …" suffix).

## Running it yourself

```bash
pip install -r requirements.txt
python collector/collect.py --local data/store      # writes to a local folder instead of R2
```

Needs `BLIZZARD_CLIENT_ID` / `BLIZZARD_CLIENT_SECRET` in the environment (not needed in Claude's
cloud sessions, where the proxy supplies the key).

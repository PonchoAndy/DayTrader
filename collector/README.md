# Collector

- `collect.py`: the hourly collector. GitHub Actions runs it at :27 past each hour
  (`.github/workflows/collect.yml`), writing to the Cloudflare R2 bucket `daytrader-data`.
- `probe.py`: one-off exploration: pulls a snapshot and reports sizes, houses and item-name coverage.
- `blizzard.py`: shared API client.
- `items.py`: item names. IDs are permanent, so each is looked up once: WoW Forever's item database first, then retail WoW's (same IDs; Forever's own database is incomplete). Unknown IDs are retried weekly.

## What's in the bucket

| Path | What | Kept |
|---|---|---|
| `raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<auctions\|commodities>.json.gz` | Blizzard's responses, gzipped (~10 MB per snapshot) | ~7 days (R2 lifecycle rule on `raw/`) |
| `hourly/<YYYY-MM-DD>/<snapshot>.parquet` | One row per house × kind × item: listings, quantity, min / p10 / p25 / median / max unit price (copper) | a few months |
| `items/items.parquet` | Item names: `item_id, name, quality, item_class, item_subclass, inventory_type, source, checked_at`. `source` = `forever` / `retail` / `missing`. Join it to the summaries on `item_id`. | indefinitely (~0.3 MB) |
| `runs/<YYYY-MM-DD>/<HHMMSS>.json` | Log of each run: result, sizes, timings, errors | indefinitely (tiny) |
| `state/latest.json` | Last stored snapshot and each house's Last-Modified, used to skip runs with no new data | — |

`<snapshot>` is Blizzard's newest Last-Modified time across houses (`YYYYMMDDTHHMMZ`).
Percentiles are quantity-weighted: p10 is the unit price at which the cheapest 10% of units are listed.
Auction prices are buyout ÷ quantity; bid-only auctions (~0.2%) are skipped. Items are keyed by
`item_id` only for now (variants such as bonus IDs and pet species are merged).

## Running it yourself

```bash
pip install -r requirements.txt
python collector/collect.py --local data/store      # writes to a local folder instead of R2
```

Needs `BLIZZARD_CLIENT_ID` / `BLIZZARD_CLIENT_SECRET` in the environment (not needed in Claude's
cloud sessions, where the proxy supplies the key).

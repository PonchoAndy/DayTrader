# 0005. Hourly collection on GitHub Actions, data in object storage

- **Status:** Proposed — waiting on PonchoAndy/DayTrader#5 and PonchoAndy/DayTrader#6
- **Date:** 2026-11-13

## Context

Each run pulls all 15 houses (see 0003): roughly 50–100 MB of JSON. The API appears to refresh
about hourly. We want months of history without running a server.

## Decision (proposed)

- **Language:** Python.
- **Scheduler:** a GitHub Actions workflow on an hourly cron, with the Blizzard keys as
  repository secrets.
- **Storage:** Cloudflare R2 (Backblaze B2 if you'd rather not add a card).
  - Raw pulls, gzipped, kept for a short window (e.g. 7 days) for debugging and re-processing.
  - Per-item hourly summaries (min buyout, quantiles, quantity, listing count per house) as
    Parquet, kept indefinitely. These are small and are what analysis reads.
- **Dashboard:** Streamlit, reading the summaries.

## Consequences

- No server to maintain; everything is free at this scale.
- If the repo is private, hourly runs slightly exceed the 2,000 free Actions minutes a month;
  run every 2 hours or make the repo public (#5).
- GitHub may delay scheduled runs by several minutes at busy times; fine for hourly data.
- GitHub disables scheduled workflows in public repos after 60 days without commits.

## Alternatives considered

- **make.com / Zapier:** built for small payloads; multi-MB pulls and long history fit poorly.
- **Your own PC:** free, but only collects while it's on.
- **Small VPS (~$5/month):** more control; reconsider if Actions becomes limiting.
- **Storing data in git:** far too large.

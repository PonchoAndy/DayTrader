# 0005. Hourly collection on GitHub Actions, data in object storage

- **Status:** Partly accepted. **Storage: Accepted** (2026-11-13, PonchoAndy/DayTrader#6). Scheduler, language and dashboard: Proposed, waiting on PonchoAndy/DayTrader#5.
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

## Storage: what's been confirmed (2026-11-13)

- Cloudflare R2 is set up: bucket `daytrader-data`, a key scoped to Object Read & Write on that
  bucket only, card on file. You're fine paying small overage charges above the free 10 GB
  (roughly $0.015 per GB per month).
- GitHub Actions secrets: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT` (the full
  jurisdiction-specific endpoint, which already contains the account ID).
- Retention, in three layers (sizes are estimates until #9 measures real pulls):
  - **Raw pulls**, gzipped: ~7 days, deleted automatically by an R2 lifecycle rule.
  - **Hourly per-item summaries** (Parquet): a few months.
  - **Daily per-item summaries**: kept indefinitely. This is the long-term history.
- R2 keys can't be used from Claude's cloud sessions through the network-secret proxy (R2
  needs request signing), so anything touching R2 runs in GitHub Actions.

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

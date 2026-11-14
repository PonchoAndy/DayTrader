# 0006. Private repo; hourly Python collector on GitHub Actions

- **Status:** Accepted
- **Date:** 2026-11-14
- **Issue:** PonchoAndy/DayTrader#5, PonchoAndy/DayTrader#9

Accepts the scheduler and language parts of [0005](0005-hourly-collection-on-github-actions-with-object-storage.md)
(its storage part was already accepted). The dashboard choice in 0005 stays Proposed.

## Context

0005 worried that a private repo's 2,000 free Actions minutes a month wouldn't cover hourly runs.
The first real pull (#9) took about 13 seconds for all 15 houses, so a run is roughly a minute
including setup. Blizzard refreshes the data hourly at about :17 past the hour.

## Decision

- **The repo stays private.**
- **Language:** Python (`collector/collect.py`).
- **Scheduler:** GitHub Actions (`.github/workflows/collect.yml`), every hour at :27, plus a
  manual "Run workflow" button. Runs with no new data store nothing but a small log entry.
- **Secrets** in GitHub Actions: `BLIZZARD_CLIENT_ID`, `BLIZZARD_CLIENT_SECRET`, plus the R2
  secrets from 0005.
- **What's stored per snapshot** in R2: the raw responses gzipped (~10 MB, kept ~7 days) and one
  per-item summary table (~0.6 MB Parquet). Layout in `collector/README.md`.

## Consequences

- ~720–1,000 Actions minutes a month (GitHub rounds each run up to a whole minute), within the free 2,000.
- Scheduled workflows only run from the default branch (`main`), so collection starts once the
  workflow is merged.
- Hourly summaries are ~0.6 MB each, ~430 MB a month; the daily roll-up from 0005 (kept indefinitely)
  is follow-up work.
- Private repos aren't subject to GitHub's 60-day inactivity pause for public repos' schedules.

## Alternatives considered

- **Public repo:** unlimited minutes, but exposes the code and analysis; not needed now.
- **Every 2 hours:** halves minutes but misses every other refresh; unnecessary given the run time.

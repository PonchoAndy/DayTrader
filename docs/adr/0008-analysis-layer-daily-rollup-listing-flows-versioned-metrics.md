# 0008. Analysis layer: daily roll-up, listing flows and versioned metrics

- **Status:** Partly accepted (listing flows kept 90 days, 2026-11-14; extra trading measures, 2026-11-15; posting-behaviour measures, 2026-11-15); the rest proposed
- **Date:** 2026-11-14
- **Issue:** PonchoAndy/DayTrader#26, PonchoAndy/DayTrader#10

Extends [0007](0007-keep-hourly-summaries-three-months-then-review.md) with a new 90-day data class.
**Accepted so far (owner, 2026-11-14):** start saving listing flows, kept 90 days, backfilled
before the first raw pulls expire; and extend raw-pull retention from 7 to 14 days until the
backfill has run (then set it back).
**Also accepted (owner, 2026-11-15, #40):** the flows job also saves four trading measures from the
raw data, as summed counts per item per hour, following the Strategist's requirements catalog
(`docs/designs/2026-11-15-data-requirements-v1.md`, rows 4–12 and 16): the price position of units
that vanished early (at the cheapest, within 5%, within 20%, above); listing age when it vanished,
in bands (needs first-seen times carried across days); depth near the cheapest price (units and
gold within +2/5/10/25%); and undercut counts (new listings below the previous cheapest). Partial-buy
value is kept separately from early vanishings, and the time-left mix of new and current listings is
recorded.
**Also accepted (owner, 2026-11-15):** four posting-behaviour measures, also hourly counts from the
raw data (`docs/designs/2026-11-15-strategy-intents.md`, N1 and follow-up signals 25–28): the
**lot-size and lot-value mix of new listings** (a before/after baseline for the deposit change at
the 2026-11-17 maintenance), a **rough seller count** (distinct lot sizes and repost patterns at
the cheapest price), **expiry waves** (units by time-left bucket and by when they were first seen),
and **"wall" listings** (the largest single lot near the cheapest price, and its price). Still open: day boundary, penny floor, normal-price window,
page refresh (design report §7, questions 3–6).

Drafted by the Architect agent; full design report in
[`docs/designs/2026-11-14-analysis-layer.md`](../designs/2026-11-14-analysis-layer.md).

## Context

The prototype and the Overnight demo each compute their own numbers from hourly snapshots. We need
one agreed set of metrics (normal price, sale rate, volatility, deal score) per auction house and
product (item + version), plus a permanent daily history. Hourly summaries hold totals only. Listing
IDs exist only in raw pulls, which are deleted after 7 days. Without IDs, sales can't be told apart
from new posts, cancels or expiries. How TSM computes its metrics is still being researched (#10),
so formulas must be able to change later. Missed hours happen (#28).

## Decision

- A new once-a-day GitHub Actions job (`daily.yml`) processes every complete day still in the raw
  window that has no current output. It catches up after failures and can be re-run.
- **Listing flows** (`flows/<YYYY-MM>/<day>.parquet`, kept 90 days): per house × kind × item ×
  version × hour, units newly posted, units vanished by last time-left bucket, units partly
  bought, a guessed repost count, and the capped value of early vanishings. Built from raw pulls by
  matching listing IDs between consecutive hours.
  *Update 2026-11-16 (#69, #81):* "early" (sold or cancelled) vs. expired is judged from each
  listing's duration (2/8/24 h, read from its first time-left bucket), not its last bucket; files
  built from 2026-11-16 carry `early_units` / `expired_units` and the cancel-check columns
  (`suspect_cancel_units`, `suspect_cheap_units`, `cancel_flag`). See `collector/flows.py`.
- **Daily roll-up** (`daily/<YYYY-MM>/<date>.parquet`, kept forever): price percentiles
  (low/median/high of hourly p10, median p25 and median), quantity open/close/low/median/high,
  hours seen, net drain, and the day's flow sums. Every row carries region, ruleset, house, faction.
  The day runs [10:00–10:00 UTC, the US trading day | 00:00–24:00 UTC] *(open question)*.
- **Metrics** (`metrics/latest.parquet`) are derived and rebuilt daily from one shared Python module
  with a `FORMULA_VERSION`. Stored data holds ingredients, never formula results. Deal %, flood or
  shortage, cross-house gaps and trade profit are computed when read.
- Outliers: never use max or plain averages of listing prices. Drop days more than 4x off the
  window median. Cap value figures. Signals need a normal price of at least 5 silver and a
  profit of at least 0.20 g per unit (settings).
- Metrics are per house and per item version; never summed across houses or versions.
- Pages read a small JSON export (`exports/app-latest.json`) committed to a branch by a manual
  workflow switch.

## Consequences

- A sale-rate estimate that separates sales from expiries, available from the first collected hour
  if flows are backfilled before the first raw pulls expire (~2026-11-21). *Update 2026-11-15: raw is kept 14 days for now (#38), so ~11-28; the backfill ran on 2026-11-15 (#37).*
- Formula changes cost nothing: from daily rows for all history; from flows and hourly data for 90
  days; from raw data for 7 days only.
- About 155 more Actions minutes a month and ~2.2 GB for 90 days of flows (estimates); daily files
  ~1.3 GB a year. Total stays under R2's free 10 GB for about 2.5 years.
- New R2 lifecycle rule `expire-flows-90d`. Flows join the hourly-data review in #33.
- The collector gains a `ruleset` column (ADR 0003); otherwise it is unchanged.

## Alternatives considered

- **Totals only:** free, but sales hidden by new posts are invisible and expiries look like sales;
  impossible to fix after raw pulls expire.
- **Per-listing archive:** most flexible (~4 GB per 90 days, ~16 GB a year forever); held in
  reserve if #10 shows formulas need per-listing detail.
- **Flows inside the hourly collector:** same data, but risks doubling collector minutes and adds
  failure modes to the job that must never miss.

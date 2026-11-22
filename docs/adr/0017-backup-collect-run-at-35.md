# 0017. A backup collect run at :35 past each hour

- **Status:** Accepted
- **Date:** 2026-11-22 (owner chose it on #28 on 2026-11-20; built 2026-11-22)
- **Issue:** PonchoAndy/DayTrader#28

## Context

Blizzard serves only the newest auction snapshot and replaces it once an hour (at :17 until 2026-11-18,
now about :25 US and :22 Europe). A run that starts after the next refresh loses that hour for good.
The collector runs at :05 (ADR 0006, moved from :27 on 2026-11-15), and GitHub usually starts scheduled
runs 29–63 minutes late. Some runs start 95–110 minutes late, though. Stored hours in R2:

| UTC day | Hours lost (US) |
|---|---|
| 11-18 | 02, 08, 14 |
| 11-19 | 02, 08, 14 |
| 11-20 | 08, 14 |
| 11-21 | 02, 08 |
| 11-22 | 08 (to 20:00) |

That's about 2–3 hours a day, nearly always the 02, 08 and 14 UTC slots, in both regions. Run logs
(`runs/<day>/`) show the runs did happen, just too late: for example, 11-20's 14:05 slot started at 15:52.
Lost hours also hide sales (a listing posted and sold inside a lost hour is never seen). The 11-22
full-market report had 13% of hours missing.

On #28 the data survey (2026-11-20) offered three fixes. (a) A backup cron. (b) An outside timer, such as a
Cloudflare Worker that starts the workflow on the hour; this needs a GitHub token stored outside GitHub.
(c) Accept the loss. The owner chose (a).

## Decision

- Add a second schedule, `35 * * * *`, to `.github/workflows/collect.yml`. It runs the same `collect` job
  as the :05 slot.
- Whichever run comes second in an hour finds Blizzard's Last-Modified unchanged, stores nothing ("no new
  data") and exits. The hourly flows and ticker steps only read what's new.
- Both slots share the `collect` concurrency group, so they never run at the same time.

## Consequences

- Every hour gets two chances. A :05 run that starts 95–110 minutes late is covered by the previous hour's
  :35 run, which lands around :10–:35 of the next hour. The health check (`report.py`, `hours_missed`)
  shows whether it works; check after about 3 days.
- **Cost: +744 GitHub Actions minutes a month** (GitHub bills each run as at least 1 minute). The estimate in
  `docs/SYSTEMS.md` rises to about **1,950 of the 2,000 free minutes**. If they run out, GitHub's default is
  to stop all jobs until the next month, which would lose far more hours than this saves. So:
  - the owner should set a small Actions spending limit (Settings → Billing), so an overage costs a few
    cents instead of stopping the collector; or
  - if the minutes are short, drop the backup to the risky slots only (e.g. `35 1,7,13 * * *`, ~93 a
    month), or move to option (b).
- At 01:35 the backup and the nightly flows job start together in the same concurrency group; the
  collect run waits, or the 02:05 run replaces it. No data is lost by that.

## Alternatives considered

- **(b) An outside timer** (Cloudflare Worker → `workflow_dispatch`): it starts runs on time, costs no extra
  GitHub minutes and could replace both crons. It needs a GitHub token kept in Cloudflare. It's still the
  fallback if minutes run short.
- **Backup only at the risky slots** (01:35, 07:35, 13:35): ~93 minutes a month. Cheaper, but it bets that
  the late slots stay where they are. The owner chose full coverage.
- **(c) Accept the loss:** 2–3 hours a day is too much for hour-of-day patterns and sale rates.

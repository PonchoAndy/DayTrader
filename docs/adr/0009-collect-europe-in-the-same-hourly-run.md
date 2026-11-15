# 0009. Collect Europe's auction data as well, in the same hourly run

- **Status:** Accepted (owner, 2026-11-15, all suggested defaults on #51)
- **Date:** 2026-11-15
- **Issue:** PonchoAndy/DayTrader#51

Supersedes the region part of [0003](0003-us-region-horde-primary-collect-all-houses.md)
("US region only"). The rest of 0003 stands: all houses, Normal ruleset, Horde as the default
view, region/ruleset/faction/house as settings.

**Owner's answers (2026-11-15):** start Europe in the shared hourly run; keep Europe raw pulls 14 days;
backup if the shared run can't stay under a minute = a separate Europe run with a $5/month GitHub
spending budget; decide Europe listing flows after #37 has timed the US job (before ~11-30); probe
Korea and Taiwan once now and decide after the Europe test (~mid-December).

## Context

0003 chose the US only ("no need to worry about EU", #2). The Strategist has since suggested that
other regions may give an early signal for US prices (signal 33,
`docs/designs/2026-11-15-strategy-intents.md`). Europe's evening is about 6–8 hours before the
US's. Blizzard serves only the latest snapshot, so history we don't collect is lost for good.
Europe (measured 2026-11-15): same 15 house IDs as the US, refreshed at :18–:19, 127 MB per pull
(US 85 MB). House IDs repeat across regions. GitHub Actions minutes (2,000 a month free, whole
minutes per job) are the tight limit; the US uses about 1,074–1,384 a month including the
planned daily job.

## Decision

- Collect **Europe (`eu`, ruleset 2) every hour in the same job as the US**, with downloads run
  in parallel so that one run stays under 60 seconds. The US is stored first; a Europe failure
  never stops the US from being stored. Regions are a setting (`REGIONS=us,eu`).
- Europe data lives under an `eu/` prefix (`eu/raw/`, `eu/hourly/`, `eu/runs/`, `eu/state/`).
  US paths stay unchanged. Item and variant names (`items/`) are shared and looked up through
  the US API.
- Keep **Europe hourly summaries 90 days** and **Europe raw pulls 14 days** for now (R2 rules
  `eu-expire-raw-14d`, `eu-expire-hourly-90d`). Europe listing flows are decided separately once
  #37 has measured the US flows job, before the first Europe raw pulls expire.
- Every key, join and view includes `region`. Regions are never mixed or summed. Cross-region
  comparisons use % changes, each region against its own history, side by side.
- Europe is data only: trading advice stays US. Cross-region signals are "unproven" until the
  Analyst's test (hypotheses H-R1–H-R4 in the #51 design) passes, about 4 weeks after start.
- Go/no-go: median run at most 45 s and 95% of runs at most 55 s. If missed, run Europe as a
  separate job with a small GitHub spending budget (owner's choice on #51).

## Consequences

- About +0 Actions minutes if the target holds (worst case +744 a month if every run goes over).
- About +8.2 GB in R2 at steady state, about $0.10 a month in overage.
- The hourly job does a little more work: more code, run-time monitoring (`job_seconds`).
- New R2 lifecycle rules for `eu/`. Readers need a region setting; the US stays the default.
- KR and TW: one probe now, decision after the Europe test.
- Follow-ups: Europe flows decision; the Analyst's lead test; region selector in pages;
  a per-region trading-day boundary (#44).

## Alternatives considered

- **Wait:** free, but loses 168 Europe hours a week and the 11-17 deposit-change comparison.
- **Separate Europe job:** cleanest separation, +744 minutes a month, over the free tier at the
  high end; needs a paid budget or risks stopped jobs.
- **Europe every 2 hours:** +372 minutes, loses half of Europe's hours.
- **Summaries only (no Europe raw):** saves about 4.7 GB and a few seconds per run, but rules out
  Europe flows and posting-behaviour measures for good.
- **Public repo:** unlimited minutes, but reverses 0006 and exposes the code and analysis.

Full design: [`docs/designs/2026-11-15-other-regions.md`](../designs/2026-11-15-other-regions.md).

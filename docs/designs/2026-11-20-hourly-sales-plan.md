# Plan: sales data every hour instead of nightly

- **Date:** 2026-11-20 · **Status:** owner chose the suggested options (US only first; 3-day parallel run; skip an
  hour when short on time). Steps 1–2 built 2026-11-20.
- **Issue:** PonchoAndy/DayTrader#104 · **Changes:** ADR 0008's "a daily job" for listing flows (a new ADR when decided)

## Why sales arrive late today

"Units sold" comes from **listing flows** (`collector/flows.py`, #37, ADR 0008). Flows compare every listing between
two hourly snapshots: what vanished early (sold), what expired, what was bought out of a listing that stayed up. They
also run the cancel checks (#69, #81). The comparison needs both snapshots' full listings, which live only in the raw
pulls in R2. So a **nightly job** (01:35 UTC, about 20:35 ET) reads a whole UTC day of raw pulls and writes one flows
file per day. Sales for an hour show up between 1 and 36 hours later. On the Ticker that's the gap where the sales
line stops short of the price bars.

## What makes hourly possible

1. **No rule looks ahead.** Each hour's flows depend only on that hour, the hour before and saved state: the
   first-seen times of each listing, and the last 24 hours of new listings for the burst check. Computing an hour
   right after it's collected gives the **same numbers** the nightly job gives later. Nothing gets revised.
2. **The hourly run already has the current snapshot.** The collector downloads and parses every listing each hour;
   it just throws the listing IDs away after summarising. Today's nightly job spends most of its ~12 s per hour
   re-downloading and re-parsing that same raw JSON.
3. **Skipped hours are already handled.** When GitHub skips a run (#28, ~3 a day), the next pair simply spans 2 hours
   (`hours_between = 2`), as it does in the nightly job.

## The design

Add a **flows step to the hourly collect job** (US first), after collection, in the same job so there's no extra
billing unit:

- **Read the new raw pull** just stored (as built: a separate step that re-reads it, ~10 s for the US, to keep the
  collector itself untouched; handing over the parsed listings in memory is a later optimisation if time gets tight).
- **Save a compact "previous hour" table** to R2 each hour: `state/hourly/tail.parquet`, with the listings of the
  snapshot just processed (id, house, kind, item, variant, qty, price, time-left), about 3–5 MB. Next hour reads it
  instead of re-downloading raw.
- **Run one hour of the existing `flows()` function** on (previous table, current listings, first-seen state, burst
  history). Write `flows-hourly/<YYYY-MM-DD>/<snapshot>.parquet` and update the step's own state in
  `state/hourly/` (first-seen times, 24 hours of new units per item, the last snapshot's listings).
- **Guards:** the step runs only if collection succeeded, stops if the job clock passes ~45 s, and never fails the
  job. If it misses an hour, the next run computes the longer pair, or the nightly job fills it from raw.
- **The nightly job becomes the assembler and safety net.** For each finished day it stitches the hourly files into
  the usual `flows/<YYYY-MM>/<day>.parquet`, so every reader keeps working unchanged. It computes any missing hour from
  raw, then deletes that day's hourly files. Its `--rebuild` switch still rebuilds everything from raw.
- **Readers get the newest hours at once:**
  - `collector/ticker.py` also reads `flows-hourly/` for days not yet assembled. The Ticker's sales line then runs up
    to the latest hour.
  - `collector/pulse.py` (the Analyst's export) can do the same later. It isn't needed now.

## Cost

- **Actions minutes (the tight limit):**
  - The hourly job is ~22 s today. This adds an estimated 6–10 s for the US: no download, flows maths ~3–5 s,
    state reads and writes ~2–3 s. That stays inside the one-minute billing unit.
  - The nightly US flows job (~190 min/month) shrinks to a short assembly (~1–2 min a night).
  - So this should **save about 140 minutes a month**.
  - Risk: if a run creeps past 60 s it bills 2 minutes. The 45 s guard and a week of `job_seconds` logs watch for that.
- **R2:** about 24 extra small writes a day per region, and hourly files that live for a day or two. Pennies.
- **Europe** (#56): the same step would add about 8–12 s more. Europe stays nightly until the US version has run a week.

## Steps

1. **Refactor `flows.py`** so one hour-pair runs from in-memory tables and saved state (no behaviour change). Replay
   one stored day hour by hour and check that the result **matches the nightly file exactly**, row for row.
   *Data engineer, then review.*
2. **Hourly step, US, in parallel:** write `flows-hourly/` each hour while the nightly job keeps running unchanged.
   After 3 days, compare totals per item and per hour; they should match exactly. Also check `job_seconds`.
3. **Switch over:** the nightly job assembles from hourly files and fills gaps; the hourly step owns the state.
   Update the Ticker export to read the newest hours; sales lag drops from 12–36 h to about 1 h.
4. **Write it down:** a new ADR (hourly flows, superseding the "daily job" part of ADR 0008); update
   `collector/README.md`, `docs/SYSTEMS.md` (minutes), the Ticker notes and the Analyst's notes.
5. **Later, optional:** Europe hourly (with #56); the Analyst's pulse export reading the newest hours.

About 2 work sessions for steps 1–2, then a short one for step 3 after the 3-day check.

## Choices for the owner

| # | Choice | Options | Suggested |
|---|---|---|---|
| 1 | Which regions go hourly | **US only first**, Europe after a week / both now | US only first |
| 2 | Parallel run before switching | **3 days** / 1 day / a week | 3 days |
| 3 | When the hourly step is short on time | **Skip that hour; the nightly job fills it** / let the run go over a minute | Skip; nightly fills it |

## Risks

- **Run time creeping over a minute** (doubles billing for that run). Mitigated by the 45 s guard, the measurement in
  step 2, and keeping the nightly job as the safety net.
- **State getting out of step** (two jobs writing `first_seen`). Avoided by giving the state to the hourly step only
  after the switch (step 3); during the parallel run the hourly step keeps its own copy.
- **A bad hour** (e.g. a house missing from a pull) is the same risk as today; the nightly assembly can recompute any
  hour from raw within the 14 days raw is kept (#38).

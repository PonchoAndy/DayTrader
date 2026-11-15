# Design: collecting other regions (Europe first) (2026-11-15)

The Architect agent's second job (#51), and the first run after its instructions were fixed (owner/builder
split, sourced deadlines, real figures). Its decision is drafted as
[ADR 0009](../adr/0009-collect-europe-in-the-same-hourly-run.md) (Proposed at the time; accepted 2026-11-15).

## Review notes (main session)

- **The fixes worked.** Part 1 is plain language with a separate deadlines section; every deadline shows
  its working; examples use real figures (Thorium Bar's reset, Copper Ore's drain) and the one invented
  example row is labelled.
- **Caught real mistakes of ours:** `collector/README.md` and ADR 0006 still said the run starts at :27
  (it's :05 since #28); the #37 issue title still had the old ~11-21 deadline (now ~11-28); SYSTEMS.md
  used 720 runs a month instead of 744 for a 31-day month, and its "billed 2 minutes" for Europe assumed
  downloads one at a time. All fixed.
- **Caught a real trap for the build:** house IDs are the same numbers in the US and Europe, and there's
  one `state/latest.json`; mixing them would break the US "no new data" check. Its `eu/` prefix layout
  avoids both.
- **Assumptions it flagged, not verified:** Forever's maintenance days per region (US Tuesday, Europe
  Wednesday is retail WoW), GitHub runner bandwidth, and the 32–47 s run-time estimate for a parallel
  two-region run. Build step 3 measures the run time before Europe is switched on.

---

# Collecting other regions (Europe first): design and costs (issue #51)

# Part 1, for the owner

## 1. Summary

- **My recommendation:** start collecting Europe now, inside the same hourly run that already collects the US. Change that run so it downloads both regions at the same time instead of one after the other.
- **Why the same run:** GitHub charges every run as at least one whole minute. If one run still finishes in under a minute, Europe costs nothing extra in GitHub time. A second, separate run would add about 744 minutes a month, and we only get 2,000 free.
- **What we'd keep for Europe:** the same hourly price summaries as the US, kept 90 days. Also the full raw downloads for 14 days, so we can still build Europe's sales estimates later if you want them. We decide that once the US version (#37) has been timed.
- **Cost:** storage goes about 7 GB over Cloudflare's free 10 GB, which is roughly **$0.10 a month**. GitHub time should be about zero extra, but we must measure it before relying on it.
- **Is the early-warning idea sound?** Partly. Europe's evening comes about 6 hours before the US evening, so news-driven moves (a newly discovered use for an item, speculation on announced changes) may show up there first. Moves caused by local supply can't carry over, because the two regions share no gold and no items. Weekly game changes probably reach the **US first**, not Europe. Europe also gives us a second, separate market for checking whether a pattern we find in the US is real. All of this is an untested idea until the Analyst checks it on about 4 weeks of data.

## 2. The problem and constraints

**The problem.** We want an hourly record of Europe's auction houses, starting as soon as possible. The goal is to test whether Europe warns us early about US price moves. It must not put the US collection at risk, and it must not push us past GitHub's free monthly time, because then GitHub stops every job, including the US one. This is for you as a US trader. Europe is data only; nobody trades there.

**Constraints**

| Constraint | Where it comes from |
|---|---|
| Blizzard only serves the latest snapshot. Any hour we don't collect is gone for good. | PLANNING §1; recap Gotchas |
| GitHub gives 2,000 free minutes a month of run time (its machines running our jobs) for a private repo. Each job is rounded up to a whole minute. If the minutes run out, jobs stop until the next month. | SYSTEMS "Where the limits bite"; ADR 0006 |
| The US hourly run takes 36–49 seconds, so it's billed 1 minute. 744 runs in a 31-day month means 744 minutes. | Brief; SYSTEMS |
| The daily sales-estimate job (#37) will also use minutes. The estimate is 10–20 minutes a day (about 310–620 a month), but it hasn't been measured. | SYSTEMS; analysis-layer design §review |
| Europe: the same 15 houses (IDs 110–125, no 122). Updated at :18–:19 past the hour. 127 MB per pull, about 1.5 times the US's 85 MB. Downloaded in 11 seconds from Claude's session. | Brief (measured 2026-11-15); SYSTEMS |
| **The US and Europe use the same house numbers.** "House 113" exists in both and means two completely different markets. | Brief; collector code |
| Cloudflare R2 (the online storage where our data is kept) is free up to 10 GB. Above that it costs about $0.015 per GB per month, and you've said small overage is fine. | ADR 0005 |
| Only GitHub's machines can write to R2, not Claude's sessions. Claude also can't read GitHub's job logs. So results have to be exported, the way the demo switch already does it. | ADR 0005; recap Gotchas |
| Region, ruleset, faction and house are settings, never hard-coded. | ADR 0003 |
| Your words on #2: "US, no need to worry about EU." That's why ADR 0003 says US only. This design reverses it for data collection only. | Issue #2 comments; ADR 0003 |
| Korea and Taiwan can't be tested from Claude's session (those addresses are blocked there). | Brief |

**Is the early-signal idea sound? My reasoning, all to be tested:**

- **Clocks (November, no daylight saving):**
  - Europe's evening, 19:00–23:00 Central European time, is about **18:00–22:00 UTC**.
  - The US evening is about **00:00–04:00 UTC** (Eastern) to **03:00–07:00 UTC** (Pacific). Our data matches this: US listings peak at 05:00–07:00 UTC (PLANNING).
  - So every day, Europe trades through its evening **about 6–8 hours before** the US does.
  - Korea and Taiwan have their evening at about 10:00–15:00 UTC, roughly 14 hours before the US.
- **Weekly maintenance order.** In regular WoW, the US has maintenance on Tuesday (about 15:00 UTC) and Europe on Wednesday morning. That's my knowledge of the game, not verified for WoW Forever. The Forever deposit change is due on **Tuesday 2026-11-17** (PLANNING, official), which fits. If so, **game changes reach the US about half a day to a day before Europe.** For those changes the US is the early market and Europe is the late one. We can check this ourselves: maintenance shows up as hours where Blizzard's data stops updating.
- **What can carry over between regions.** Only *information* crosses between them; gold and items can't. Examples:
  - **Newly discovered uses for an item**, spread through Wowhead, Reddit or YouTube.
  - **Speculation on announced changes.** Blizzard posts during US working hours, which often lands in Europe's evening first.
  - **Shared progress.** Both regions launched together, so demand for levelling materials moves on the same calendar. That makes Europe a *second sample* for checking US patterns, not an early warning.
- **What can't carry over.** Anything driven by local supply:
  - One seller buying out a market, like the Thorium Bar reset on house 113 (units fell from about 1,200 to 100 and the cheapest-10% price went from 0.16 g to 0.25 g).
  - Floods of new listings, bots, local price levels, and gaps between factions or the Blackwater house.
  - Penny items whose price jumps from one copper step to the next.
- **A trap for the analysis.** Both regions have a daily rhythm, and Europe's comes first. A naive comparison would make *every* item look like Europe leads. The test must remove each region's own time-of-day pattern first.

## 3. Options

All minute figures are for a 31-day month (744 hourly runs). The US alone already uses about **1,074–1,384** of the 2,000 free minutes: 744 for the hourly run, 310–620 for the daily job (#37), and about 20 for manual runs.

**Option 1: Wait.**
- Costs nothing.
- Every week we wait loses 168 hours of Europe's history for good.
- It also misses the deposit change on Nov 17/18, which is a ready-made test of which region reacts first.

**Option 2 (recommended): Europe in the same hourly run, with downloads done in parallel.**
- **How it works:** today the run downloads 30 files one after another. Downloading 8 at a time, across both regions, should cut download time from about 19–29 seconds (US alone) to about 10–15 seconds for both. That figure is an estimate.
- **My estimate for the whole run:** 32–47 seconds, so still billed 1 minute.
- **Safety:** the US is saved first. A Europe failure or slowdown never stops the US from being stored.
- **Minutes:** about +0. If 1 run in 10 goes over a minute, that's +74. If every run went over, +744, which is why we measure first.
- **Storage:** Europe summaries for 90 days, about 3.5 GB, plus Europe raw downloads for 14 days, about 4.7 GB. That's **about $0.10 a month** in overage.
- **Effort:** two build sessions, plus a few minutes of your time in Cloudflare.
- **Risk:** the timing estimate could be wrong. The first build step measures it before we switch Europe on.

**Option 3: A separate hourly run for Europe.**
- The cleanest separation. The US run isn't touched at all.
- It costs **+744 minutes**, bringing the total to 1,818–2,128, which is over the free limit in a 31-day month at the high end.
- It only works if you allow a little paid usage on GitHub. SYSTEMS puts it at roughly half a cent a minute, so about $1 a month, or about $6 if Europe's sales estimates are added later. Without that, GitHub stops the jobs and the US loses hours too.
- A cheaper version runs Europe every 2 hours instead (+372 minutes), but it loses half of Europe's hours.

**Option 4: Make the repo public.**
- Public repos get unlimited free minutes, so any of the above becomes free.
- It reverses ADR 0006 and shows your code, analysis and strategy notes to everyone.
- I mention it only for completeness.

**Why I recommend Option 2.** It's the only option that adds Europe at about zero cost and keeps us well inside the free minutes. It also keeps room for the daily job (#37) and for the backup hourly slot still being considered on #28.

**What would make me switch:**
- If the measured run regularly goes past about 55 seconds, switch to Option 3 with a small paid budget, or to Europe every 2 hours.
- If Europe shows no early signal after 8 weeks, cut Europe back to summaries only, or stop collecting it.

**Korea and Taiwan.** Their evening comes first of all, but their markets (and the guides players there read) differ more from the US, so news may travel less directly. They can't be tested from Claude's session. I suggest one test download from GitHub now, which costs about 2 minutes. Then decide after the Europe test, around mid-December.

## 4. Deadlines and things that can't be undone

- **Every week we wait loses 168 hours of Europe for good.** Working: 24 runs a day × 7 days, and Blizzard only serves the latest snapshot (PLANNING §1). Europe's auction data has existed since 2026-11-06 (PLANNING), so about 10 days, roughly 240 hours, of its launch period is already gone.
- **2026-11-17 (Tuesday) maintenance, with the deposit change** (PLANNING, official). It's the first chance to see which region reacts first to a game change. Europe's maintenance is probably Wednesday 11-18 (my assumption from regular WoW). To have a "before" picture for Europe, Europe must be running **before that maintenance, ideally from 11-16 or 11-17**. Comparing Europe's lot sizes before and after needs the raw downloads, so Europe raw must be kept from the first day.
- **Europe's sales estimates must be decided within 14 days of Europe's start.** Raw downloads are the only source for them, and they'd be deleted after 14 days. If Europe starts 11-16, its first raw downloads disappear around 11-30. The US timing from #37 (due before 2026-11-28, recap) arrives just in time to decide.
- **The folder layout becomes permanent** once the long-term daily history starts (#26), because that history is kept forever. Pick it now (Part 2).
- Without automatic clean-up rules (lifecycle rules: Cloudflare settings that delete files after a set number of days), Europe adds about 336 MB a day. This is fixable later, but it costs money until it's fixed.

## 5. Open questions for you

1. **Start Europe now in the shared hourly run (Option 2)?** The choices are Option 1, 2 or 3. **Suggested: yes, Option 2.**
2. **Keep Europe's raw downloads for 14 days** (about $0.07 a month) so its sales estimates can be added later? The other choice is summaries only. **Suggested: keep them for 14 days.**
3. **Backup if the shared run can't stay under a minute.** The choices are:
   - (a) a separate Europe run, with a GitHub spending budget (I suggest $5 a month; it needs a card on GitHub);
   - (b) Europe every 2 hours, for free;
   - (c) drop Europe's raw downloads to save time.
   **Suggested: (a).** A $5 budget is also worth having as insurance for the US alone: it pays about half a cent per extra minute instead of letting jobs stop.
4. **Sales estimates for Europe**: none, Horde houses only (about half the data, an estimated 230–465 minutes a month), or all houses (465–930 a month). **Suggested: decide when #37 has measured the US job, before about 11-30.**
5. **Korea and Taiwan**: test once now, then decide after the Europe test (about mid-December)? Or skip them? **Suggested: test once now.**

---

# Part 2, for whoever builds it

## 6. The design

**Data flow**

```
collect.yml  (cron :05, one job, env REGIONS=us,eu)
  step 0: echo JOB_STARTED=$(date +%s) >> $GITHUB_ENV
  collect.py --regions us,eu
    ├─ Api("us") ─┐  ThreadPoolExecutor(8): houses list, then 30 GETs per region,
    ├─ Api("eu") ─┘  all 60 in flight together (one requests.Session per thread)
    ├─ US: gzip+put raw → summarize → put hourly → state → run log   (stored first)
    ├─ EU: same, under the eu/ prefix; own state; own errors; deadline
    └─ items.update(store, us_api, ids_from_both)  (US API only; IDs are global)
R2 daytrader-data
  raw/ hourly/ runs/ state/ flows/ daily/   ← US, unchanged (legacy: "no prefix = us")
  eu/raw/ eu/hourly/ eu/runs/ eu/state/ (eu/flows/ eu/daily/ later)
  items/ (shared by all regions)
```

**Layout decision: put the region first for every region except the US.** Use `eu/<class>/...` and keep the US at the root.

- `report.py` lists `hourly/` recursively, so a `hourly/eu/...` layout would silently mix Europe into US reports. `eu/hourly/...` can't be picked up by any existing US reader.
- Lifecycle rules match by prefix, so `eu/raw/` and `eu/hourly/` get their own rules with no overlap. That also sidesteps the question of what R2 does when two rules overlap, which I haven't checked.
- Add a helper `prefix(region) -> "" if region == "us" else f"{region}/"`, used by every reader and writer. The region stays a setting (ADR 0003).
- I don't recommend migrating the US into `us/`: it touches the job that must never miss, for no gain.

**Things the build must not get wrong (found in the code):**

- **State file collision.** There is one `state/latest.json` today. If Europe wrote to it, the US "no new data" check would compare against Europe's timestamps. Use a separate `eu/state/latest.json`.
- **House IDs repeat across regions.** Every key, join, group-by and cache must include `region`: hourly, flows, the first-seen state carried across days, metrics, exports and the page filters. The rule "never sum across houses or versions" (ADR 0008) extends to regions. Listing IDs may also repeat across regions (unverified), so flows matching must stay within one region.
- **Item lookups through the US API only.** `items.update` uses the `api` it's given (`static-forever-{region}`, `static-{region}`, locale `en_US`). Pass the US `Api` and the union of both regions' IDs. The first Europe run may bring a few hundred new IDs: two calls each, 8 workers, about 0.15 s per call (estimate), so roughly 10–20 s once. That's a one-off 2-minute run, which is acceptable. Optionally cap new lookups per run at about 300.
- **Faction names.** Confirm `faction_of()` parses Europe's house names with `locale=en_US`. The main session reports the same faction layout; the build should assert that no house comes back "Unknown".
- **Concurrency.** Keep one job. If Option 3 is ever used, give the Europe workflow its own `concurrency` group. With two workflows in one group, a newly queued run cancels the one already waiting.

**Making the run fit in 60 seconds (estimates; working shown)**

- **Today, US alone:** 36–49 s end to end. The download takes 19–29 s on GitHub (#28 comment). That leaves 17–20 s for setup, processing and upload.
- **Both regions one after another:** download 19–29 s plus Europe at about 1.5 times that (29–44 s) = 48–73 s. Add processing of about 17–20 s plus about 12 s for Europe. Total 77–105 s, billed 2 minutes. This confirms the SYSTEMS table's Option A, but only for downloads done one at a time.
- **Downloads in parallel (8 at a time):**
  - The download becomes roughly the larger of the slowest single response and the total time ÷ 8: (48–73) ÷ 8 is about 6–9 s.
  - Bandwidth sets a floor. 212 MB at about 200 Mbit/s is about 8.5 s; the runner's bandwidth is an assumption. Call it **10–15 s**.
  - Processing: JSON parsing plus summaries for 212 MB, about 7 s, with gzip on worker threads overlapped (zlib releases the GIL), about 12–20 s in all.
  - Setup can be trimmed from about 15 s to about 8–10 s by caching the virtualenv or using `uv`.
  - **Total: about 32–47 s.** Private-repo runners are assumed to be 2 vCPU / 7 GB; memory is not a concern, since about 212 MB of response bytes are held and parsed one file at a time.
- **Go / no-go target:** median at most 45 s, and 95% of runs at most 55 s, across at least 24 runs. Record `job_seconds = now - JOB_STARTED` in each run log. If the target is missed, first lower gzip to level 1 (faster, files perhaps 10–20% larger, which is cheap). Then fall back as in question 3.
- **Protecting the US:**
  - Process and store the US as soon as its futures complete.
  - Europe gets a per-request timeout of 30 s, 2 retries, and an overall deadline of about 120 s from job start. After that, log `{"result": "deadline"}` and skip Europe.
  - Exit non-zero if either region mostly failed, but only after everything else has been stored, so failures show as red runs.

**Europe's hourly summary: identical schema to the US** (plus `ruleset`, which #37 adds)

| column | type | example (numbers invented, for illustration) |
|---|---|---|
| snapshot | timestamp UTC | 2026-11-16 18:18 |
| region | str | "eu" |
| ruleset | int16 | 2 |
| house_id | int | 113 |
| faction | str | "Horde" |
| kind | str | "commodities" |
| item_id | int64 | 12359 (Thorium Bar, ID from memory; check items.parquet) |
| variant | str | "" |
| listings, quantity | int64 | 40, 1150 |
| min/p10/p25/median/max_price | int64 copper | 1400, 1550, 1650, 1900, 9000 |

Path: `eu/hourly/<YYYY-MM-DD>/<snapshot>.parquet`. Raw: `eu/raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<kind>.json.gz`. Runs: `eu/runs/<date>/<HHMMSS>.json`, which adds `job_seconds`.

**Storage arithmetic (estimates)**

- **Europe raw:** 127 MB ÷ about 9 (the US gzip ratio, 85 → 9.3 MB) is about 14 MB per hour. 24 × 14 days × 14 MB = **4.7 GB** (2.35 GB at 7 days).
- **Europe hourly:** 1.3–2.0 MB each (the US is 1.3 MB / 107k rows; Europe has more listings, but the number of distinct item versions grows less). 24 × 90 × about 1.6 MB = **3.5 GB** (range 2.8–4.3).
- **Bucket at steady state:** US about 9 GB while US raw stays at 14 days (7.5 GB at 7 days), plus Europe about 8.2 GB, is about 15.7–17.2 GB. That's 5.7–7.2 GB over the free 10 GB, × $0.015 = **$0.09–0.11 a month**.
- **Writes:** about 33 per region per hour, so about 49k a month in total, against 1M free.
- **Blizzard API calls:** about 62 an hour, against a limit of 36,000.

**Minutes table (31-day month)**

| | US only | + Option 2 | + Option 3 |
|---|---|---|---|
| Hourly | 744 | 744 (+0–74) | 1,488 |
| Daily job #37 (US, unmeasured) | 310–620 | 310–620 | 310–620 |
| Manual | 20 | 20 | 20 |
| **Total** | **1,074–1,384** | **1,074–1,458** | **1,818–2,128** |
| + Europe sales estimates, all houses (1.5 × US) | | +465–930 | +465–930 |
| + Europe sales estimates, Horde only (about 49% of listings: US Horde 453k of 932k) | | +230–465 | +230–465 |
| + backup slot (#28) | +744 | +744 | +744 |

Note: Europe's sales estimates and the #28 backup slot can't *both* fit in the free tier.

**Hypotheses for the Analyst** (write them down before looking at the data)

- **Item set:** listed in both regions in at least 80% of hours, normal price at least 5 silver (ADR 0008's floor), same faction compared (Horde vs Horde).
- **Series:** each region's own index, the median across its non-empty Horde houses of p10 as a % change from its own 7-day median, **with that region's hour-of-day pattern removed**. Compare % changes, never gold, and never pool the two regions.
- **H-R1, news-led moves lead.** An "EU event" is a p10 move of at least 30% that holds for 3 or more snapshots. After an EU event, the US moves the same way by at least half as much within 6–30 h at least 1.5 times as often as the US base rate at matched times. Test both directions: if the US "leads" Europe equally, the cause is shared news, not a lead.
- **H-R2, game changes reach the US first.** After the 11-17 deposit change, the shift in cheap or small listings appears in the US before Europe. Also find each region's maintenance window from gaps in Last-Modified.
- **H-R3, supply moves don't carry over.** EU reset or flood signatures (quantity change of at least 50% within 1–2 h) predict nothing in the US beyond the base rate. If they seem to, suspect a method error.
- **H-R4, replication.** Patterns found in the US, such as the drain of levelling materials (Copper Ore −87%, Mithril Bar −81%), also appear in Europe on the same calendar. Europe is then an out-of-sample check.
- **Window:** build thresholds on Europe weeks 1–2 (to about 11-30). Test on weeks 3–4 (to about **2026-12-14**). Extend to 8 weeks (to about 2027-01-11) if there are fewer than 30 EU events.
- **Stop rule:** if H-R1 fails at 8 weeks, cut Europe to summaries only, or keep it only for replication.
- **Until H-R1 passes,** signal 33 stays "advisors only, unproven" (strategy-intents §4).

**Pages** (a note for the Designer, #48)

- Region is a selector like house and faction. The default is US. No table ever mixes regions.
- The one cross-region view is a % change chart with two labelled lines and each region's evening shaded on a UTC axis.
- The trading-day boundary (#44) must be a per-region setting. The US uses 10:00 UTC; Europe's quiet hour would be about 04:00–05:00 UTC (estimate).

## 7. Conflicts with past decisions

- **0003:** direct conflict with "Collect from the US region only" and "EU too: not needed" (owner on #2). ADR 0009 supersedes **only the region part** of 0003. The rest stays: all houses, the Normal ruleset, Horde as the default view, settings never hard-coded.
- **0005 / 0006:** no conflict; this extends the stored layout. 0006's estimate of about 720–1,000 minutes holds if the shared run stays under 60 s. Stale text spotted: 0006 and `collector/README.md` still say the run starts at :27; `collect.yml` uses :05.
- **0007:** no conflict. Europe hourly uses the same 90 days through its own rule.
- **0008:** compatible. Flows stay out of the hourly job, and Europe flows are deferred. "Never summed across houses or versions" extends to regions. The flows and first-seen keys must include region. The minutes estimates disagree (0008 about 155 a month, SYSTEMS 300–600); #37 will measure it.
- **SYSTEMS.md corrections:**
  - Option A's "billed 2 min" assumes downloads one at a time.
  - Use 744 runs for a 31-day month, not 720.
  - Option B's "+~11 GB" is for the full pipeline only.
  - The #37 title's deadline of "~2026-11-21" predates the move to 14-day raw retention (11-28).

## 8. Draft ADR

```markdown
# 0009. Collect Europe's auction data as well, in the same hourly run

- **Status:** Proposed
- **Date:** 2026-11-15
- **Issue:** PonchoAndy/DayTrader#51

Supersedes the region part of [0003](0003-us-region-horde-primary-collect-all-houses.md)
("US region only"). The rest of 0003 stands: all houses, Normal ruleset, Horde as the default
view, region/ruleset/faction/house as settings.

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
```

## 9. Proposed Build issues

1. **Build: per-region storage layout and state (`eu/` prefix)**
   - **Who:** Claude. **Blocked by:** ADR 0009 accepted.
   - **Done when:** a `prefix(region)` helper is used by collect.py and report.py. `--region eu --local` writes `eu/raw`, `eu/hourly`, `eu/state`, `eu/runs`, and US paths are unchanged. Item lookups go through the US API. No Europe house comes back "Unknown". This can be tested from Claude's session, since the Europe host is allowed there.
2. **Setup: R2 lifecycle rules for Europe**
   - **Who:** owner (Cloudflare → R2 → `daytrader-data` → Settings → Lifecycle rules). **Blocked by:** nothing.
   - **Done when:** `eu-expire-raw-14d` (prefix `eu/raw/`, 14 days) and `eu-expire-hourly-90d` (prefix `eu/hourly/`, 90 days) exist.
3. **Build: fast two-region hourly run (parallel downloads, US first, Europe deadline, `job_seconds`)**
   - **Who:** Claude. **Blocked by:** 1.
   - **Done when:** at least 5 manual runs from the branch store both regions to R2. Run-time figures are exported by committing a file, as the demo switch does (Claude can't read logs or R2). Median at most 45 s; result posted on #51.
4. **Build: switch Europe on in the hourly schedule, plus per-region health in the report**
   - **Who:** Claude, then the owner merges. **Blocked by:** 2, 3. Aim for before the 11-17/18 maintenance.
   - **Done when:** 24 h of Europe snapshots with 0 US hours lost, and the job-time distribution is exported. SYSTEMS.md, collector/README.md and PLANNING §5 are updated.
5. **Research: probe KR and TW from GitHub Actions (manual switch, results committed)**
   - **Who:** Claude. **Blocked by:** nothing (low priority).
   - **Done when:** PLANNING records each region's houses, size, refresh minute and download time.
6. **Decide: Europe listing flows (none / Horde only / all)**
   - **Who:** owner. **Blocked by:** the #37 run-time measurement.
   - **Done when:** answered before the first Europe raw pulls expire (Europe start + 14 days, about 11-30).
7. **Research: is Europe an early signal for US prices? (H-R1–H-R4)**
   - **Who:** Claude (Analyst, #19, if built). **Blocked by:** 4 weeks of Europe data (about 2026-12-14).
   - **Done when:** hit rates against base rates, and the maintenance order, are in PLANNING with a keep / cut / stop recommendation.

## 10. Files and issues read

- `CLAUDE.md`
- `docs/SYSTEMS.md`
- `docs/PLANNING.md`
- `docs/WORKFLOW.md`
- `docs/adr/README.md`, `template.md`, `0003`, `0005`, `0006`, `0007`, `0008`
- `docs/sessions/2026-11-15.md`
- `docs/designs/2026-11-15-strategy-intents.md` (follow-up section)
- `docs/designs/2026-11-14-analysis-layer.md` (grep)
- `docs/designs/2026-11-15-data-requirements-v1.md` (grep: no region requirements)
- `collector/README.md`, `collect.py`, `blizzard.py`, `items.py`, `report.py` (grep)
- `requirements.txt`
- `.github/workflows/collect.yml`
- Issues:
  - #51 (no comments)
  - #2 (comments: "US, no need to worry about EU")
  - #28 (comments: pulls take 19–29 s; hours lost)
  - #37 and its comments
  - #38 (comments)
  - the open-issue list
- **Not verified, marked in the text as assumptions:**
  - US/EU maintenance days and times for Forever
  - GitHub's per-minute price and runner size for private repos
  - runner bandwidth to the Europe host
  - whether listing IDs are unique across regions
  - Europe gzip ratio and summary size
  - how R2 handles overlapping lifecycle rules (avoided by the layout)

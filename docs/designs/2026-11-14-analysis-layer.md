# Design: the analysis layer (2026-11-14)

The first job of the Architect agent (`.claude/agents/architect.md`, PonchoAndy/DayTrader#16). The
brief asked for the daily roll-up, core metrics, and where they're computed and read (#26, #10). Its
decision is drafted as [ADR 0008](../adr/0008-analysis-layer-daily-rollup-listing-flows-versioned-metrics.md)
(Proposed). The run took about 5 minutes and read 12 files plus 5 GitHub issues.

## Review notes (main session)

Checked against the repo after the report came back:

- **Correct:** hourly rows have no `ruleset` column (`collect.py` adds region, house, faction only).
  It's a real gap against ADR 0003 that nobody had noticed.
- **Correct:** the core argument. Listing IDs exist only in `raw/` (7 days), and totals can't
  separate sales from new posts and expiries.
- **Small error:** the backfill deadline. The first snapshot in R2 is `20261114T0017Z`, stored
  2026-11-14 ~01:05 UTC (the 23:17 snapshot it mentions was a local probe, never uploaded). So the
  oldest raw pulls expire around **2026-11-21**, not 11-20. ADR 0008 uses 11-21.
- **Likely optimistic:** "about 5 minutes a day" for the flows job. Each hour's raw pull is ~85 MB
  of JSON, so a day means parsing ~2 GB. That could take 10–20 minutes. It's still well inside the
  free minutes, but Build issue 1 should measure it.
- **Example row:** the made-up Copper Ore prices (~38 s) are far above the real ~0.02 g. It labels
  them as made up, but real figures from PLANNING would have been better.
- **Too technical for its reader in places** (column types, int16). The agent file asks for column
  types in the design section, so that's the definition's doing, not a failure of the agent.

---

## The Architect's report (verbatim)

### 1. Summary

**Recommendation: totals alone are not good enough for sale rate. Start saving per-hour "listing flows" now, while the raw pulls still exist.** A flow row says, for each product in each hour, how many units were newly posted, how many vanished early (sold or cancelled), how many vanished near the end of their time (probably expired), and how many were partly bought. A new once-a-day job computes flows from the raw pulls already in R2 by comparing each hour with the previous one. The collector doesn't change. The same job writes the daily roll-up. Formulas ("normal price", sale rate, volatility) live in one shared Python module with a version number, and a small metrics table is rebuilt from it every day. Stored data holds only ingredients (counts and prices), so changing a formula after #10 costs nothing and loses nothing. The pages (prototype, demo, `report.py`) all read one exported JSON file built by that module, instead of each computing their own numbers. The deadline is real: the first raw pulls (from 2026-11-13 23:17) are deleted by the 7-day rule around **2026-11-20 or 21**. If the flows job runs before then, it can rebuild flows for every hour we have collected. After that, those hours can only ever have totals.

### 2. The problem and constraints

**The problem.** Today each page works out its own "drain", "gap" and "swing" from the hourly snapshots. When this is built, there should be one agreed set of numbers per auction house and product (item + version): a normal price, an estimated sale rate, volatility and a deal score. There should also be a permanent daily history that survives after hourly data expires. The owner uses this to decide trades in their own house. Later the advisor agents will read the same numbers.

| Constraint | Source |
|---|---|
| Raw pulls (every listing, with its ID) kept 7 days. Hourly summaries kept 90 days. Daily kept forever. | ADR 0007; R2 rules `expire-raw-pulls-7d`, `expire-hourly-summaries-90d` |
| Hourly summaries hold totals only: listings, quantity, min/p10/p25/median/max price. No listing IDs and no time-left. | `collector/README.md`, `collect.py` `SUMMARY_COLUMNS` |
| Raw listings have `id`, `quantity`, price, and a `time_left` bucket (SHORT / MEDIUM / LONG / VERY_LONG). | PLANNING "First real snapshot" |
| Region, ruleset, faction and house are settings, so every stored row needs region, ruleset, house and faction. | ADR 0003. **Gap found:** the hourly table has `region`, `house_id`, `faction` but **no `ruleset` column**. |
| Metrics are per house, never summed across houses. Versions are separate products. | Owner direction (#11 comment) |
| Missed hours will happen (2 of 13 lost so far). | #28 comment |
| 2,000 free Actions minutes a month. The collector uses ~720, or ~1,440 with the second slot. | Brief, ADR 0006, #28 |
| R2 can't be read from Claude's sessions, so data reaches pages only through a workflow. | Session gotchas, ADR 0005 |
| Scheduled workflows run only from `main`. A new workflow file can't be dispatched until it's on `main`. | Session gotchas |
| Absurd listings exist (a fish at 9,999,999 g). Penny items swing hundreds of percent: the median p10 swing is 23%, and 1 in 10 swing more than 186%. | PLANNING "First night"; 2026-11-14 recap |
| We don't know TSM's formulas yet. | #10 is open with no comments |
| R2 free tier is 10 GB. Small overage is OK, about $0.015 per GB per month. | ADR 0005 |

GitHub tools were available. I read #10, #11, #26, #28 and #33 with their comments, and they match the brief.

### 3. Options (for the key question: how to estimate sales)

**Why totals can't tell you sales.** Between two hours, the change in total units listed = new posts − sales − cancels − expiries, all mixed together. In the US evening, people post Copper Ore about as fast as others buy it. Total units barely move, so totals say "nothing sold" when plenty did. Overnight, Copper Ore fell 87%, partly because posting stops while old listings expire, so totals count expiries as sales. Only listing IDs separate these cases, and listing IDs exist only in the raw pulls for 7 days.

**Option A: totals only (do nothing yet).** Sale rate = the sum of hour-to-hour drops in total units ("net drain"). It costs nothing. But it's a rough lower bound that can't tell sold from expired. If #10 later shows we need more, the history before that point is lost for good.

**Option B: listing flows, computed once a day from raw pulls (recommended).** A daily job loads each hour's raw listings and matches them by listing ID against the hour before. It counts units as new, vanished early, vanished near expiry, or partly bought, and records the price of what vanished. It writes one row per house × kind × product × hour, only where something changed. Estimated cost: about 2 GB at 90 days and about 5 minutes of run time a day. It can be re-run for any day still in the 7-day raw window, and that window is also the safety buffer if the job fails.

**Option C: a per-listing archive.** Keep a slim record of every listing: ID, product, quantity, price, first and last time seen, and last time-left bucket. Any future formula can be re-run on exact listings. Estimated cost: about 4 GB at 90 days, or about 16 GB a year if kept forever.

**Variant of B: compute flows inside the hourly collector.** Same output, but it adds roughly 10 seconds of work to every run. That risks pushing runs past one billed minute, which would double the collector's minutes. It also puts new failure modes into the one job that must never miss.

**Recommendation: B, run as a daily job.** It keeps what can't be rebuilt and leaves the collector alone, for about 150 minutes a month and about 2 GB. The first week of output also answers the question with real numbers: if flow-based and totals-based estimates agree closely, we can stop flows at the February review (#33). **Switch to C (90-day retention) if** #10 shows the formulas need per-listing detail, such as how long a listing sat or exact prices of sold listings. Option B's job builds the listing tables anyway, so adding C later is a small change.

### 4. The design

```
Blizzard ─hourly─► collect.py (unchanged, plus a ruleset column)
                     ├─ raw/…json.gz          (7 days)  ──┐
                     └─ hourly/…parquet       (90 days) ──┤
                                                          ▼
                 daily.yml, once a day (new) ── analysis/ module, FORMULA_VERSION
                     ├─ flows/<YYYY-MM>/<day>.parquet   per-hour flows (90 days)   ← from raw
                     ├─ daily/<YYYY-MM>/<day>.parquet   daily roll-up (forever)    ← hourly + flows
                     ├─ metrics/latest.parquet          normal price etc. (rebuilt daily)
                     └─ exports/app-latest.json         small file for pages
                                                          ▼
           "export" switch (manual) commits the JSON to a branch → prototype / demo artifacts
```

**Day boundary.** One choice can't be undone later: where a "day" starts. I suggest the **US trading day**: 10:00 UTC to 10:00 UTC, which is about 2 am Pacific, labelled by US date. It's the quietest hour, so the US evening peak (05:00–07:00 UTC) stays inside one day. This is Open question 5. The examples below assume it.

**How the job runs.** It processes every day that is complete, still in the raw window, and either missing a daily file or built with an older rollup version. So it catches up by itself after a failed day, and can be re-run for any date (re-running overwrites). Schedule: about 10:45 UTC.

#### (a) The daily table, `daily/<YYYY-MM>/<date>.parquet` (kept forever)

One row per day × house × kind × item × version. Prices are in copper.

| Column | Type | Meaning |
|---|---|---|
| `date` | date | Trading day |
| `region`, `ruleset` | str, int16 | "us", 2 |
| `house_id`, `faction`, `kind` | int16, str, str | 113, Horde, commodities |
| `item_id`, `variant` | int32, str | Item ID; bonus ID ("" = no version) |
| `hours_in_day` | int8 | Snapshots stored that day across the whole bucket, e.g. 22 of 24 |
| `hours_listed` | int8 | Snapshots where this product had at least 1 listing |
| `min_price_low` | int64 | Cheapest unit seen all day |
| `p10_low`, `p10_med`, `p10_high` | int64 | Lowest, median and highest of the hourly p10 |
| `p25_med`, `median_med` | int64 | Median of the hourly p25 and of the hourly median |
| `qty_open`, `qty_close`, `qty_low`, `qty_med`, `qty_high` | int32 | Units listed at the first and last hour, and the low, median and high |
| `listings_med` | int32 | Median listing count |
| `net_drain_units` | int32 | Sum of hour-to-hour drops in units. Totals-only; available back to the first day. |
| `flow_hours` | int16 | Hours covered by flow comparisons. Null if no flows. |
| `new_units` | int32 | Units newly posted |
| `gone_units_short`, `gone_units_medium` | int32 | Vanished while in the shortest time-left buckets (likely expired) |
| `gone_units_long`, `gone_units_very_long` | int32 | Vanished early (sold or cancelled) |
| `partial_units` | int32 | Units bought out of a listing that stayed up (commodities): a certain sale |
| `relist_guess_units` | int32 | Early vanishings matched by a same-size, cheaper new listing in the same hour. Likely cancel-and-undercut; a guess. |
| `gone_early_cheap_units` | int32 | Early vanishings priced at or below the previous hour's p25 (likely bought) |
| `gone_early_value` | int64 | Copper value of early vanishings plus partial buys, each unit price capped at 2× the previous hour's median |
| `rollup_version` | int8 | Version of the roll-up code that wrote the row |

Example row (made-up values, to show the shape): `2026-11-15, us, 2, 113, Horde, commodities, 2770 (Copper Ore), "", 23, 23, 3100, 3400, 3800, 5200, 4100, 4600, 8200, 1450, 900, 4300, 9100, 61, 7350, 23, 5900, 410, 380, 1900, 2100, 2650, 300, 3200, 26_500_000, 1`. In words: Copper Ore usually sat at about 38 s for the cheap end (p10 median) and 41 s a quarter of the way up. Units ranged from 900 to 9,100. 2,650 units were partly bought (sure sales) and 4,000 vanished early, 300 of which looked like reposts.

Estimated size: about 120k rows a day (hourly holds 107k, and more products appear across a day than in one hour). At about 30 bytes a row compressed, that's about 3.5 MB a day, or about 1.3 GB a year.

#### (b) What's stored and what's computed when read

**Stored and rebuilt daily** in `metrics/latest.parquet` (derived, safe to delete), for each house × kind × item × version:
- `normal_price`: median of the daily `p25_med` over the last N days (N is a setting; see Open question 4). Days more than 4× above or below the window's median are dropped first.
- `normal_days`: how many days fed the normal price.
- `sold_per_day`, `sell_through`, `sold_basis`, `net_drain_per_day`: sale-rate figures, defined in (c).
- `intraday_swing_pct`: median over the window of (p10_high − p10_low) / p10_med.
- `day_to_day_pct`: median absolute % change of `p25_med` between consecutive days.
- `qty_typical`: median of `qty_med`.
- `signal_ok`, `confidence`, `formula_version`, `computed_at`.

About 120k rows, roughly 3 MB. It's stored rather than computed in the page because it needs 7–14 days of history.

**Computed when read**, because these depend on the latest hour and on settings: deal % = 1 − current price ÷ normal price (using the latest `min_price` for the cheapest unit and `p10` for buying a real amount; "good" means 70% of normal or less, as in PLANNING §3), flood/shortage = latest quantity ÷ `qty_typical`, cross-house gaps and Blackwater bridge profit (they depend on fee settings), and goods value.

**What can be recomputed, from what, for how long:**

| Change you might want later | Rebuild from | Possible for |
|---|---|---|
| New flow categories or matching rules | `raw/` | last 7 days only |
| New daily price or quantity columns | `hourly/` | last 90 days |
| New daily flow sums | `flows/` | last 90 days |
| Any formula built from stored ingredients (normal price, sale rate, volatility) | `daily/` | all history, at daily resolution |

So #10 can change any formula freely, as long as it uses those ingredients. Anything needing per-listing detail only works from the switch-on date (Option C).

#### (c) Sale rate, and what must start being saved

**What the flows job saves.** It writes `flows/<YYYY-MM>/<day>.parquet`. The key columns are `snapshot`, `prev_snapshot`, `hours_between`, region, ruleset, house, faction, kind, item and variant. The count columns are the same as the daily flow block in (a), plus listing counts. Listings are classified by matching listing IDs between consecutive hours:
- only in the previous hour: gone, bucketed by its last `time_left`
- in both, with lower quantity: partial buy
- only in the current hour: new

Estimated size: about 64k changed rows an hour × about 15 bytes ≈ 1 MB an hour. That's about 24 MB a day, or about 2.2 GB at 90 days.

**Sale-rate formula v1** (in the shared module, easy to replace):
- `sold_per_day` = (partial_units + gone_units_long + gone_units_very_long − relist_guess_units) ÷ flow_hours × 24
- `sell_through` = that sold figure ÷ (sold + gone_units_short + gone_units_medium). It's a rough "share of postings that sell", the same idea TSM's sale rate is reported to capture.
- Fallback when no flows exist: `net_drain_per_day`, labelled "lower bound".

**Things to treat with care:**
- **Time-left buckets in Forever are unverified.** Retail uses roughly <30 min / 30 min–2 h / 2–12 h / 12–48 h, from memory. Forever may use Classic's lengths. That's why the buckets are stored as they are and interpreted only in formulas.
- **Whether a partly bought commodity listing keeps its ID is an assumption.** Build issue 1 measures it.
- **The repost count is a guess.** We can't see sellers, and common stack sizes (20) will cause false matches, so it's stored separately.
- **TSM, from memory and unverified:** my recollection is that TSM's sale rate comes from players' own addon sales records, which we don't have, and that DBMarket weights about 14 days of the cheap end of listings. #10 should confirm this.

#### (d) Missed hours and outliers

**Missed hours.** `hours_in_day` versus `hours_listed` separates "nobody listed it" (sold out, which matters) from "we have no snapshot" (unknown). Medians ignore the gaps. A flow comparison across a gap records `hours_between = 2`, and rates divide by real hours covered. Listings posted and sold inside a gap are invisible, so sale rates undercount a little on gap days. Days with fewer than 12 snapshots are flagged and left out of normal price.

**Outliers.** Metrics never use `max_price` or plain averages of listing prices. The percentiles are weighted by quantity, so one 9,999,999 g fish can't move p10 or p25 unless it is nearly the whole supply. Normal price drops any day more than 4× away from the window median. Goods value per product is capped at the smaller of its median and 3× normal price, times quantity. Vanished-listing value is capped at 2× the previous hour's median.

**Penny floor** (settings):
- A product produces % signals only if its normal price is at least 5 silver. That's the demo's current filter.
- A trade must clear at least 0.20 g profit per unit after the cut. That's the prototype's current filter.

`confidence` is low when there are fewer than 3 days of history or the median listing count is below 3.

#### (e) What the pages read

The daily job writes `exports/app-latest.json` to R2. A manual **export** switch in `collect.yml`, like `demo`, commits it to a branch, and the main session then rebuilds the artifact. For each house it holds every product that passes the floor, with its label (name + version), the metrics from (b), and the latest hour's min/p10/p25/qty, plus the fee settings. Target size is under about 2 MB; my estimate is about 25k products across 15 houses × 10 numbers. The artifacts' size limits are an assumption I haven't checked.

- **Prototype (`tools/data-tour/`):** floods, shortages, gaps and bridge trades come from this file instead of its own ad hoc filters.
- **Overnight demo:** keeps its hourly series (last 48 h) and adds `sold_per_day` and `normal_price`. Its "demand" pick changes from "drain" to `sold_per_day`.
- **`report.py`:** imports the same module.

Notes for #33 (where hourly detail is genuinely needed): the daily roll-up's high/low and open/close columns, the demo's hour-by-hour series, and re-running daily flow sums for up to 90 days. Flows themselves come from raw pulls, not from the hourly summaries.

**Costs (estimates):**
- **Actions minutes:** about 5 min/day × 31 days ≈ 155 min/month. That makes 720 + 155 = 875, or 1,440 + 155 = 1,595 with the second slot.
- **Storage at steady state:** raw 1.6 GB + hourly 2.7 GB + flows 2.2 GB = 6.5 GB, plus daily 1.3 GB a year. That stays under 10 GB for about 2.5 years, then costs pennies a month.

### 5. Conflicts with past decisions

- **0003:** No conflict, but a gap in what's built: hourly rows lack `ruleset`. The fix is to add it in the collector and fill 2 for older rows in the roll-up.
- **0005:** Consistent: daily kept forever, analysis runs in Actions. The dashboard choice is untouched; pages read a JSON export, and Streamlit could read the Parquet files directly.
- **0006:** No conflict. It adds about 155 Actions minutes a month beyond its estimate.
- **0007:** Extends it, doesn't supersede it. It adds a new 90-day class (`flows/`) to the storage totals and puts it in the #33 review.

### 6. Draft ADR

Saved as [ADR 0008](../adr/0008-analysis-layer-daily-rollup-listing-flows-versioned-metrics.md), with the deadline corrected to ~2026-11-21.

### 7. Open questions for the owner

1. **Start saving listing flows (Option B)?**
   - Choices: yes, kept 90 days; yes, kept forever (about 8 GB a year); or no, totals only.
   - **Default: yes, 90 days.** The daily sums keep their essence forever anyway.
2. **Temporary insurance: lengthen the raw-pull rule from 7 to 14 days until the flows backfill has run?**
   - Cost: about 1.6 GB more for a couple of weeks. It's one change in Cloudflare R2 → bucket → Settings → Lifecycle rules → `expire-raw-pulls-7d`.
   - **Default: yes, then set it back.** I'm assuming R2 applies a changed rule to existing objects; this is unverified.
3. **Penny floor.**
   - Choices: 5 silver normal price and 0.20 g profit, or 1 g and 1 g.
   - **Default: 5 s and 0.20 g.** These are settings, so they're easy to change.
4. **Normal-price window.**
   - Choices: 7 days or 14 days (TSM-like).
   - **Default: 7 days while the game is new.** Prices are still trending after the 11-04 launch. This is free to change later.
5. **Where a "day" starts.** This can't be redone once hourly data expires.
   - Choices: 10:00 UTC (US trading day, quietest hour) or midnight UTC (simpler).
   - **Default: 10:00 UTC.**
6. **Page refresh.**
   - Choices: on demand through a workflow switch, or a daily automatic commit.
   - **Default: on demand.** Daily commits would add about 2 MB a day to the repo's history.

### 8. Proposed Build issues

1. **Build: listing flows from raw pulls, with backfill**
   - **Who:** Claude
   - **Blocked by:** owner's OK on Q1
   - **Urgent:** must run before about 2026-11-20.
   - **Done when:**
     - `flows/` exists for every hour still in `raw/`.
     - It measures whether partly bought commodity listings keep their ID, and the share of each `time_left` bucket among vanished listings.
     - It compares flow-based and totals-based sale estimates for one week of hours on house 113. Results go in PLANNING and #10.
     - Run time is recorded.
   - **Note:** test through a temporary `collect.yml` switch, because a new workflow can't be dispatched until it's on `main`.
2. **Setup: R2 lifecycle rule `expire-flows-90d` (and optional raw 14 days)**
   - **Who:** you
   - **Blocked by:** Q1, Q2
   - **Done when:** the rules are listed in R2.
3. **Build: daily roll-up (revises #26)**
   - **Who:** Claude
   - **Blocked by:** 1, Q5
   - **Done when:**
     - `daily.yml` is on `main`, runs daily, and catches up missed days.
     - `daily/` files hold the columns in (a).
     - `collect.py` writes `ruleset`.
     - `collector/README.md` is updated.
4. **Build: shared metrics module and `metrics/latest.parquet` (formula v1)**
   - **Who:** Claude
   - **Blocked by:** 3, Q3, Q4
   - **Done when:**
     - The metrics in (b) are rebuilt daily, with `formula_version`.
     - `report.py` uses the module.
     - A Metrics section in PLANNING lists the formulas.
5. **Build: app-data export and pages read it**
   - **Who:** Claude
   - **Blocked by:** 4, Q6
   - **Done when:**
     - An `export` switch commits `app-latest.json`.
     - The prototype and demo show normal price and sale rate from it.
     - Their ad hoc calculations are removed.
     - A #33 comment notes the demo's hourly use.

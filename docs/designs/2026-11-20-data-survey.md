# Data survey: are we collecting enough? (2026-11-20)

**Brief:** the owner asked every agent whether the data we collect is enough for its goals, and if not, what it
needs. All seven answered: Strategist, Economist, Analyst, Researcher, Architect, Designer and Data engineer. Each
got the same brief (what we collect, the exports, the earlier catalogs, the deadlines). Combined by the main session.
The source catalogs are `2026-11-15-data-requirements-v1.md` and `2026-11-15-stockpile-positions-review.md` §6.

## Bottom line

- **What we collect each hour is enough.** All seven agree. The US listing flows already cover most of v1's "collect now
  or lose" rows.
- **The gaps are about keeping data and collecting it reliably**, plus some reference data that can be fetched at any time.
- **Two things have hard deadlines:**
  - the **launch-period raw pulls** expire from ~**11-28** (US) and ~**11-29** (EU);
  - we lose **about 3 hours a day** because GitHub sometimes never starts a scheduled run.

## Save now or lose it

| # | Need | Who asked | Why | How | Deadline |
|---|---|---|---|---|---|
| S1 | **Archive the launch-period raw pulls** (US 11-14 → 11-27; EU 11-15 → if wanted) to a folder with no delete rule | Architect, Analyst, Strategist, Economist | Flows can only be rebuilt from raw. Two rule fixes already needed it (#69, #81). The tests listed below need raw. The launch glut won't happen again. | One-off workflow job. US ~5 GB, ~$0.08/month. | Decide by **11-26**; the copy must run before 11-28 |
| S2 | **Stop losing ~3 hours a day** | Data engineer, Strategist | GitHub never created some scheduled runs (run numbers are consecutive), e.g. 11-19 02:00, 08:00 and 14:00 UTC in both regions. Blizzard serves only the current snapshot, so a lost hour is gone, and flows miss listings that come and go inside the gap. | #28. A second cron costs ~+744 min/month. An outside timer (e.g. a Cloudflare Worker calling the workflow) costs ~0 minutes but needs a GitHub token stored as a secret. | Ongoing |
| S3 | **Ratify Europe flows** | Data engineer, Strategist, Analyst | The flows job has built EU since 11-15 (`REGIONS: us,eu`), so #56 is in effect option (c), but nobody ratified it. Docs still say "US only". | Close #56 as (c), or set flows to US only (saves ~7 min/day) | EU raw expires ~11-29 |
| S4 | **Owner's own sales and expiries** in the Stockpile Ledger (price, hours to sell, unsold) | Strategist, Analyst | The only ground truth for `sold_est` / `sold_clean` and the cancel check | Add sale and expiry fields to the ledger; keep a copy in git | From the next trade |
| S5 | **Daily price ladder** for ~20–50 watched items: units at 1.0×, 1.1×, 1.5×, 2× and 3× vendor, once a day, kept forever | Economist, Designer | How much sells near normal prices (exit capacity); crowding by stockpilers. Flows measure depth from the cheapest listing, not from the vendor price. | New step in the nightly flows job; launch weeks can be filled from the S1 archive | Covered by S1 if archived |

**Tests that need raw pulls** (Analyst): H2, H3, H4, H5, H13, H18, H19/H-D4, H23, H29, H-D1–D3, H-D6 and H-P1, plus the
Strategist's deep-discount listing life (v1 #16) and #84 (stacks). Without S1 these can only be run on a rolling
14-day window, never on the launch period.

## Soon

| # | Need | Who asked | How |
|---|---|---|---|
| N1 | **Daily roll-up (#26) for every day since 11-14**, with an hour-of-day price profile and whole-market totals for both regions | All except the Researcher | Build in December, so a broken job is caught before hourly data from 11-14 expires ~2027-02-12 |
| N2 | **Pulse history must never shrink.** A watchlist change or the manual **pulse** switch rebuilds from R2 and would drop anything older than 90 days. | Architect, Designer, Strategist | Take older hours from the roll-up (N1) |
| N3 | **Event log** with exact UTC times: maintenance, hotfixes, client builds, Black Market changes, raids 12-09, holidays, Hardcore | Economist, Designer, Strategist, Researcher | A dated file kept by the main session. First entries: 11-17 US maintenance with new client build 1.60.1.70959 and the deposit change; Blizzard's refresh minute moved from :17 to :25 (US) and from :19 to :22–23 (EU) on 11-18. |
| N4 | **Fees confirmed in game**: cut, deposit after 11-17, Blackwater cut, durations | Strategist, Analyst | #13, a 10-minute trip |
| N5 | **Pulse additions**: value sold per watchlist item per hour; Europe totals (`PULSE_REGIONS: us,eu`); a "normal day" band per house and hour (middle half of past days, with the day count); a whole-market price index per house and hour; missed hours and health | Analyst, Designer, Economist | Export changes |
| N6 | **Recipes**, from Blizzard's API: profession → skill-tier → recipe, with reagents and amount made (verified 2026-11-20; Blacksmithing alone has 507 recipes; no skill levels) | Researcher, Strategist | Fetch any time; skill levels from wago.tools `SkillLineAbility`. Ties into #41. |
| N7 | **Position ledger in git** (quantity, cost, date, rule) | Economist, Designer | An export or copy whenever positions change |
| N8 | **Daily health without a manual switch**. `health.json` was last made 11-16. | Data engineer, Analyst | Add missed hours to pulse, or schedule the health export |
| N9 | **Correct `docs/SYSTEMS.md`** | Data engineer | Flows take ~14 min a night (US + EU), so ~435 min/month, and the real total is ~1,250 of 2,000 minutes/month, not ~1,000. Flows files are ~64 MB per region per day: ~11.5 GB at 90 days, ~28 GB in all, ~$0.27/month. |

## Later

- **Item level, required level and stack size**: the API already sends level fields, but `items.py` drops them; stack size comes from wago.tools `ItemSparse`. Needed for the leveling-wave index and bank-slot math.
- **Classic Era auctions as a mature-economy reference**: Blizzard's API serves them (`dynamic-classic1x-us`, verified). Reference only, since it's a different game version.
- **A wider hourly watchlist** (~40 busy commodities; houses 117 Blackwater and 110/111), once the pulse can't lose history.
- **Black Market prices**, dated, monthly (owner in game).
- **Disenchant odds**: not in the game files; Wowhead or the owner's own tally.
- **Population**: can't be had from the API; the leveling-wave index stands in.
- **Can't get:** WoW Token price (the API returns 404 for Forever); the launch week 11-06 → 11-13 (lost; maybe a third-party site, unverified).

## Not worth keeping, or worth changing

- **`max` price:** mostly troll listings. It's cheap to keep, but no view should show it and the roll-up can drop it.
- **Raw at 14 days:** keep it while the flows rules are still changing (#38). Afterwards, back to 7 days saves ~5.5 GB.
- **`market.json`'s 12-hour thinning:** it hides the daily swing. Pages should read `pulse.json` for watchlist items.
- **Summary files in git don't scale for long** (Architect):
  - `market.json` already hits its 8 MB cap;
  - `pulse.json` grows ~18 MB a year;
  - every run adds a full copy to git history.
  Suggested direction, not urgent: a few standard extracts with size limits on one data-only branch that is
  replaced each run, and long history from the roll-up.
- **Collected but unused:** flows' depth, walls, crowding, undercuts, age, lot-value and time-left columns; gear and variant rows. All are cheap; keep them.

## Other findings

- **The API's Forever game data is an older build** (1.60.1.70399) than wago.tools' newest (70959, 2026-11-17).
  Where the two disagree, prefer wago.tools. Build 70959 still shows a 5% cut and deposit rate 5 at faction houses,
  and 15% / 25 at Blackwater. [datamined]
- **The first pulse run failed** on hourly files from before 11-14 ~04:00 UTC, which have no `variant` column; fixed on the work branch.
- About 0.5% of US posted units a day stay up longer than the duration we inferred for them. Worth a look when #69 is revisited.

## Decisions for the owner

1. **Archive the launch-period raw pulls (S1)?** Default **yes, US and EU, decide by 11-26**. New Decide card.
2. **Missed hours (S2, #28):** (a) second cron, ~+744 min/month; **(b) outside timer, ~0 min, needs a GitHub token as a secret**; (c) accept the loss.
3. **Europe flows (S3, #56):** **ratify (c), all houses**, since it's already running; or US only.
4. **Keep raw at 14 days (#38)** at least through the launch glut (~02-08)? Default **yes**.
5. **Move the hourly-retention review (#33)** from 02-14 to ~**02-01**, before the first files expire? Default **yes**.

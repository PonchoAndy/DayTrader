# Systems, services and costs

What DayTrader runs on, what each piece costs, and where the limits are. Last updated 2026-11-15 (house cleaning).
Prices are as we last checked them; confirm on each provider's billing page before relying on them.

## At a glance

| Service | What it does for us | Plan | Cost today |
|---|---|---|---|
| **Blizzard Battle.net API** | Source of all auction data (hourly) and item names | Free developer account, one API client | $0 |
| **GitHub** (private repo `PonchoAndy/DayTrader`) | Code, issues, decisions; **GitHub Actions** runs the hourly collector | Free plan: 2,000 Actions minutes a month for private repos | $0 |
| **Cloudflare R2** (bucket `daytrader-data`) | Stores raw pulls, hourly summaries, listing flows, item names, run logs | Free tier: 10 GB stored, 1M writes and 10M reads a month, no download fees | $0 now; ~$0.08–0.15 a month from late November |
| **wago.tools** | WoW Forever game data (variant names; recipes and vendor prices later) | Public site, no account | $0 |
| **claude.ai artifacts** | Issue Deck (with its own small database), DayTrader Prototype, Overnight Market demo | Part of your Claude plan | Included |
| **Claude Code (cloud)** | Work sessions, agents, scheduled tasks, the background Issue Deck sync session | Part of your Claude plan; uses your plan's usage | Included |
| **Streamlit Community Cloud** | Account created; not used yet (dashboard choice still open, ADR 0005) | Free | $0 |

**Total today: $0 beyond your Claude plan**, rising to roughly $0.10–0.15 a month for storage once the bucket passes 10 GB (late November).

## What's committed (running or decided)

**Data collection** (ADR 0002, 0003, 0006)
- Hourly collector on GitHub Actions at **:05** past each hour (moved from :27 on 2026-11-15, #28), plus a
  **backup run at :35** (ADR 0017, 2026-11-22) that stores nothing when the hour is already saved.
- **US and Europe** (ADR 0009), all 15 auction houses each, auctions and commodities, in **one run**:
  downloads in parallel, processing on both CPU cores, US stored first, Europe skipped for the hour
  if it's late. ~62 Blizzard API calls an hour, far under Blizzard's limit (36,000 an hour).
- Each run: **~22 seconds** (measured 2026-11-15, #54; ~41 s when the package cache is rebuilt),
  billed as **1 minute**. Before the speed-ups, US alone took 36–49 s.
- Each run log carries a **health** record (hours missed, empty or shrunken houses, Europe skipped,
  refresh minute; #18). It adds no API calls, no extra stored files and well under 0.1 s per run.

**Storage in R2** (ADR 0005, 0007, 0008, 0009), with automatic clean-up rules. Europe uses the same
folders under `eu/`.

| Folder | What | Kept | Size at steady state (est.), US + Europe |
|---|---|---|---|
| `raw/`, `eu/raw/` | Full hourly pulls, gzipped (US ~15 MB, Europe ~18 MB an hour at gzip level 1) | **14 days for now** (back to 7 once #37's measurements are done, #38) | ~11 GB at 14 days (US 5, Europe 6); ~5.5 GB at 7 |
| `hourly/`, `eu/hourly/` | Per-item summaries (~1.3–1.6 MB each) | 90 days | ~6.3 GB (US 2.8, Europe 3.5) |
| `flows/` | Listing flows + extra measures (#37, nightly since 2026-11-15; US only for now, Europe is #56). From 2026-11-16 also early/expired by duration (#69) and the cancel check (#81): ~4% larger files | 90 days | ~3 GB (estimate; measure after a week) |
| `daily/` | Daily roll-up (#26, not built yet) | Forever | +~1.3 GB a year |
| `items/`, `runs/`, `state/` | Names, run logs, collector state | Forever | tiny |

**Steady state: ~20 GB while raw is kept 14 days, ~15 GB at 7 days**, plus ~1.3 GB a year. That's
5–10 GB over the free 10 GB: about **$0.08–0.15 a month** in overage (owner OK'd small overage, ADR 0005).
Gzip level 1 (for speed, #54) made raw files ~25% bigger than the first estimates.

**Accounts, keys and secrets** (never in files)
- GitHub Actions secrets: `BLIZZARD_CLIENT_ID`, `BLIZZARD_CLIENT_SECRET`, `R2_ENDPOINT`,
  `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`.
- Claude's cloud environment "DayTrader": a network secret for Blizzard's login host, and an
  allowed-hosts list (Blizzard API US/EU, Blizzard US and EU forums, Blizzard news, Icy Veins, wowauctionhouse.com, ahledger.com, TSM,
  Wowhead, wago.tools, the WoW wiki, Warcraft Tavern, Undermine Exchange).

**Claude-side automation**
- Scheduled task "Issue Deck → active work session" (fires into the current work session when you
  press something on the Deck).
- Scheduled task "Sync the Issue Deck" and the long-lived "Issue Deck sync (background)" session
  (used when no work session is active).
- Agents in `.claude/agents/`: Architect, Strategist, Designer, Researcher, Data engineer (they run inside sessions; no separate cost, but they use your plan's usage).

## Where the limits bite

**GitHub Actions minutes are the tightest limit.** GitHub bills each job in whole minutes, so a
40-second run costs 1 minute and a 70-second run costs 2.

| Workload | Minutes a month (est.) |
|---|---|
| Hourly collector, US + Europe (1 min × 24 × 31) | ~744 |
| Backup collect run at :35 (ADR 0017, #28; 1 min × 24 × 31, even when it finds no new data) | ~744 |
| Nightly flows, US + Europe (US alone measured 2026-11-15 at ~5 min, billed 6; both regions 670–746 s on 11-21/11-22, billed ~12–13) | ~390 |
| One-off flows rebuild (`flows_rebuild` switch, #69/#81): ~5–8 min per region per day still in raw/, e.g. ~4 days × US + EU ≈ 50 min, once | (+~50 once) |
| Daily roll-up (#26, not built yet) | (+~30–60) |
| Manual report / demo / health / market runs (1 min each; market ~1–3 min once the bucket holds weeks of hourly files) | ~20–30 |
| Daily Analyst export (`pulse`, #19, from 2026-11-20): re-reads the last 3 days (~85 hourly + 4 flows files, est. 35–60 s); a manual full rebuild grows to ~5–10 min at 90 days | ~30–60 |
| **Total today** (hourly 744 + backup 744 + nightly flows US+EU ~390 + pulse ~45 + manual ~25) | **~1,950 of 2,000**: set a small spending limit (Settings → Billing) so an overage costs cents instead of stopping the collector; fallbacks in ADR 0017 |

- If the free minutes run out, GitHub's default is to **stop running jobs until the next month**
  (unless a spending limit is set; check Settings → Billing). For a collector, that means lost hours
  that can't be recovered, so we should stay well under the limit.
- Paid overage, if enabled, is roughly half a US cent per Linux minute (check current GitHub pricing):
  500 extra minutes ≈ $3–4 a month.
- A public repo gets unlimited free minutes, but ADR 0006 chose private.

**R2 is roomy.** Overage is $0.015 per GB per month: 10 GB over the free tier costs about
$0.15 a month. We're expected to pass 10 GB in late November. Writes and reads are well under the free allowance (~25k writes a month today).

**Blizzard's API** has plenty of headroom (~62 calls an hour against 36,000).
The `market` switch adds ~430 item lookups the first time (vendor prices) and only new items after that.

## Other regions

Europe: decided and running (ADR 0009, #51; live since PR #65). Korea and Taiwan: probe once (#55),
decide ~mid-December after the Europe early-signal test (#57). The options compared at the time are in
`docs/designs/2026-11-15-other-regions.md`.

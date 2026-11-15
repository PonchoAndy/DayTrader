# Systems, services and costs

What DayTrader runs on, what each piece costs, and where the limits are. Last updated 2026-11-15.
Prices are as we last checked them; confirm on each provider's billing page before relying on them.

## At a glance

| Service | What it does for us | Plan | Cost today |
|---|---|---|---|
| **Blizzard Battle.net API** | Source of all auction data (hourly) and item names | Free developer account, one API client | $0 |
| **GitHub** (private repo `PonchoAndy/DayTrader`) | Code, issues, decisions; **GitHub Actions** runs the hourly collector | Free plan: 2,000 Actions minutes a month for private repos | $0 |
| **Cloudflare R2** (bucket `daytrader-data`) | Stores raw pulls, hourly summaries, item names, run logs | Free tier: 10 GB stored, 1M writes and 10M reads a month, no download fees | $0 |
| **wago.tools** | WoW Forever game data (variant names; recipes and vendor prices later) | Public site, no account | $0 |
| **claude.ai artifacts** | Issue Deck (with its own small database), DayTrader Prototype, Overnight Market demo | Part of your Claude plan | Included |
| **Claude Code (cloud)** | Work sessions, agents, scheduled tasks, the background Issue Deck sync session | Part of your Claude plan; uses your plan's usage | Included |
| **Streamlit Community Cloud** | Account created; not used yet (dashboard choice still open, ADR 0005) | Free | $0 |

**Total today: $0 beyond your Claude plan.** Nothing below changes that unless noted.

## What's committed (running or decided)

**Data collection** (ADR 0002, 0003, 0006)
- Hourly collector on GitHub Actions at **:05** past each hour (moved from :27 on 2026-11-15, #28).
- **US and Europe** (ADR 0009), all 15 auction houses each, auctions and commodities, in **one run**:
  downloads in parallel, processing on both CPU cores, US stored first, Europe skipped for the hour
  if it's late. ~62 Blizzard API calls an hour, far under Blizzard's limit (36,000 an hour).
- Each run: **~22 seconds** (measured 2026-11-15, #54; ~41 s when the package cache is rebuilt),
  billed as **1 minute**. Before the speed-ups, US alone took 36–49 s.

**Storage in R2** (ADR 0005, 0007, 0008), with automatic clean-up rules:

| Folder | What | Kept | Size now (est.) | Size at steady state (est.) |
|---|---|---|---|---|
| `raw/` | Full hourly pulls, gzipped (~8–11 MB each) | **14 days for now** (back to 7 after the #37 backfill, #38) | ~0.3 GB and growing | 3.4 GB at 14 days; 1.7 GB at 7 |
| `hourly/` | Per-item summaries (~1.3 MB each) | 90 days | ~0.05 GB | ~2.8 GB |
| `flows/` | Listing flows + extra measures (#37, not built yet) | 90 days | 0 | ~3 GB (estimate; #37 measures it) |
| `daily/` | Daily roll-up (#26, not built yet) | Forever | 0 | +~1.3 GB a year |
| `items/`, `runs/`, `state/` | Names, run logs, collector state | Forever | <0.01 GB | tiny |

**Steady state (US only): ~7.5 GB, plus ~1.3 GB a year.** That stays inside the free 10 GB for about
two years. While raw is at 14 days it's ~9 GB.

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
- Agents in `.claude/agents/`: Architect, Strategist, Designer (they run inside sessions; no separate cost).

## Where the limits bite

**GitHub Actions minutes are the tightest limit.** GitHub bills each job in whole minutes, so a
40-second run costs 1 minute and a 70-second run costs 2.

| Workload | Minutes a month (est.) |
|---|---|
| Hourly collector, US + Europe (1 min × 24 × 31) | ~744 |
| Daily flows + roll-up job (#37, #26), US: 10–20 min a day | ~300–600 |
| Manual report/demo runs | ~20 |
| **Total, US only** | **~1,075–1,385 of 2,000** |

- If the free minutes run out, GitHub's default is to **stop running jobs until the next month**
  (unless a spending limit is set; check Settings → Billing). For a collector, that means lost hours
  that can't be recovered, so we should stay well under the limit.
- Paid overage, if enabled, is roughly half a US cent per Linux minute (check current GitHub pricing):
  500 extra minutes ≈ $3–4 a month.
- A public repo gets unlimited free minutes, but ADR 0006 chose private.

**R2 is roomy.** Overage is $0.015 per GB per month: 10 GB over the free tier costs about
$0.15 a month. Writes and reads are well under the free allowance (~25k writes a month today).

**Blizzard's API** has plenty of headroom (~31 calls an hour against 36,000).

## Scenario: adding other regions (EU first)

Probed 2026-11-15 (Europe, ruleset 2): the same 15 houses, refreshed at ~:19 past the hour, **127 MB
per hourly pull** (about 1.5× the US's 85 MB; the biggest EU house has ~170k listings against the US's
~104k), fetched in 11 seconds. KR and TW not probed yet.

| Option for EU | Extra Actions minutes / month | Extra storage | Extra cost / month |
|---|---|---|---|
| **A. Same job as US** (one run pulls both) | +744 if downloads run one at a time (over 60 s); **~+0 if downloads run in parallel** and the run stays under 60 s (the Architect's recommendation, #51) | +~11 GB at steady state | Minutes total ~1,800–2,100: at the edge of free; R2 ~$0.15 |
| **B. Separate EU job**, full pipeline (raw + flows) | +720 hourly, +300–600 flows | +~11 GB | Over 2,000 minutes: ~$2–6 overage, or jobs stop; R2 ~$0.15 |
| **C. EU summaries only** (no raw kept, no flows) | +720 (or +0 if folded into a run that stays under 60 s) | +~4 GB | Likely $0; R2 ~$0.05 |
| **D. Make the repo public** (any of the above) | Unlimited free minutes | as above | $0 for minutes; exposes code and analysis |

The Architect's design and recommendation: `docs/designs/2026-11-15-other-regions.md`, ADR 0009 (Proposed), #51.

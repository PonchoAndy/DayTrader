# Stockpile positions review — Strategist (2026-11-15)

**Brief:** review buy-and-hold positions in low-level crafting materials before any gold is committed; size, stage and
judge them; intents for a "Positions & watchlist" tool. Inputs: `2026-11-15-leveling-materials-research.md` and one live
US snapshot (2026-11-15 ~19:30 UTC). Verdicts are about **entry and risk**, not forecasts (the Economist sets horizons).
No profit is promised. Saved by the main session from the Strategist agent's report (ADR 0010).

## Part 1: for the owner

### 1. Verdicts
The draft's shape holds, with three changes: Tier A mixed "floor-protected" with "good demand" (Malachite, Tigerseye fail
on value per bank slot); **Pyrite moves to the priced sleeve** (at 1.4× vendor it can lose 28%) as its lead bet; **hold
Pyrite instead of Sulfuric Acid** (same exposure, cheaper, higher floor). Two numbers drive the verdicts: **worst case**
(loss if sold to a vendor) and **gold per bank slot** (20 × price); bank space likely binds before gold.

**Floor sleeve** (× vendor / worst case / gold per slot)

| Item | 113 | 114 | Verdict | Why |
|---|---|---|---|---|
| Pristine Hide | 1.04× / −4% / 52s | 0.98× / **+2%** / 49s | **Take (core)** | Deepest floor market (5,752 on 113); scarce tier 2, 20g beta Black Market price; long wait likely (supply grows as players reach its band). On 114 cheapest units are *below* vendor. |
| Jade | 1.05× / −5% / 1.47g | 1.03× / −3% / 1.44g | **Take** | Very rare; end-game smithing (225+); substitutes cost more. High value per slot. |
| Iridescent Pearl | 1.13× / −12% / 1.70g | 1.24× / −19% / 1.86g | **Take on 113, small on 114** | One per enchanter (Runed Golden Rod), no substitute; 59-recipe LW family. Best value per slot. |
| Shadowgem | 1.07× / −6% / 53s | 1.08× / −7% / 54s | **Small** | One per enchanter (Runed Silver Rod); otherwise a swappable family gem. |
| Lesser Moonstone | 1.00× / 0% / 1.20g | 1.03× / −3% / 1.24g | **Small** | No downside, good value per slot, weak demand. Only if slots are spare. |
| Small Lustrous Pearl | 1.07× / −7% / 43s | 1.33× / −25% / 53s | **Small on 113, skip 114** | Swappable family gem. |
| Tigerseye | 1.19× / −16% / 24s | 1.00× / 0% / 20s | **Small on 114 only** | Poor value per slot; medium, swappable demand. |
| Malachite | 1.00× / 0% / **3s** | 4.3× / −77% / 13s | **Skip** | A full slot holds 3 silver; weak demand. |

**Priced sleeve** (real fall possible, down to vendor)

| Item | 113 | 114 | Verdict | Why |
|---|---|---|---|---|
| Pyrite | 2.4× / −58% / 48s | 1.4× / −28% / 28s | **Take: lead priced bet, best on 114** | Strongest thesis; no substitute in high-level smithing (via Sulfuric Acid); beta BM ceiling 5g ≈ 35× today. On 113 only below your cap. |
| Pristine Leather | 3.2× / −68% / 79s | 2.2× / −55% / 56s | **Small** | Best demand and level-gate evidence; partly priced in. |
| Sulfuric Acid | 4.0× / −75% | 3.0× / −67% | **Skip: hold Pyrite** | 1 Acid = 2 Pyrite; on 114, 2 Pyrite 2.78s vs Acid 3.80s; Pyrite's floor is higher (2s vs 1.25s) and it has more uses. (Assumes no costly extra input/cooldown; unchecked.) |
| Bauxite | 1.6× / −38% | 2.7× / −63% | **Skip until uses are known** | No consuming recipes documented. |

**Avoid group** (Frilled Lichen, Cerulean Dye, Magenta Dye, Rosecap, Strange Dust, Moss Agate): skip for now, **watch
closely**. Vendor price isn't a floor for them (Lichen at 100× could fall 99%), the scarcity story is priced in, and we
have one snapshot. Lichen and the dyes are the best live test of the thesis (H-L3). Strange Dust has no floor (1c) and
falling demand. Moss Agate is thin, with no documented uses.

**These are two or three bets, not twelve:** Tigerseye / Shadowgem / Small Lustrous Pearl swap within recipe families
(one bet, H-L5); Pyrite / Pristine Leather / Pristine Hide share one story (scarce materials stay level-gated and
high-level demand arrives); all share gold inflation.

### 2. Sizing and staging (any budget)
1. **Pot:** a share of spare gold (default **25%**); keep the rest for training, mount, repairs, quicker trades.
2. **Split:** up to ~70% floor sleeve, ≤~30% priced sleeve, sized so a fall to vendor costs ≤~10% of *total* gold
   (e.g. 30g of Pyrite at 1.39s risks ~8.4g).
3. **Per-bet cap:** ≤~25% of the pot per item; the three swappable gems count as one.
4. **Price cap; never sweep the ladder.** Floor: **1.10× vendor** (1.05× preferred): Pristine Hide ≤2.75s, Jade ≤7.7s,
   Iridescent Pearl ≤8.25s, Shadowgem ≤2.75s, Lesser Moonstone ≤6.6s, Small Lustrous Pearl ≤2.2s, Tigerseye ≤1.1s.
   Priced: your own number (suggested Pyrite ≤1.5s, Pristine Leather ≤2.8s). Floor listings refill; let supply come to you.
5. **Value per slot:** minimum ~**50s per slot** (Malachite, Tigerseye, Strange Dust fail). 60 slots = 1,200 units ≈ 17g
   of Pyrite or ≈ 88g of Jade. A **bank alt** is the normal way to add space.
6. **Exit capacity:** until sale rates are measured, hold no more than is **listed on your house now** (113: ~600 Jade,
   ~330 Lesser Moonstone, ~420 Iridescent Pearl, ~460 Shadowgem; 114: ~1,000 Pyrite). Later: ≤ ~two weeks of the house's sales.
7. **Three tranches:** ~⅓ **today** under the caps; ⅓ **after maintenance** (US 11-17, EU 11-18 — the minimum deposit
   drops to 1c, so cheap small lots of 1s-vendor items may appear, H-P3); ⅓ **week of 11-30** with two weeks of trend data,
   only where thesis checks haven't failed. Never chase a spike.
8. **Record every purchase:** date, house, item, quantity, gold paid. We can't see bags or rebuild this later.

**Costs:** AH cut 5% (Horde/Alliance), 15% Blackwater (never exit there). Deposits follow *vendor* price (~5% per 2 h:
2 h 5%, 8 h 20%, 24 h 60%), lost if unsold, so sell floor items with **2-hour listings** or vendor them. AH break-even =
cost ÷ 0.95 + lost deposits, so floor items pay only above ~**1.2× vendor**. The vendor exit is free, instant, unlimited.
Idle gold; slots (20 per slot); **market absorption** when selling (biggest hidden cost); crowding by other stockpilers.

### 3. Weekly review
Watch on your house: price vs vendor (floor watch); units listed and posted per day; estimated sales per day; position
value **guaranteed** (vendor) and **realistic** (two-week sell-down after 5% cut); thesis checks H-L1–H-L8; events
(11-17 maintenance, raids 12-09, Hardcore, hotfixes on scarce materials or the Black Market).

| Action | When |
|---|---|
| **Add** | Under cap, supply not growing week over week, no thesis check failed; or a spike falls back under cap |
| **Hold** | Between cap and target, thesis intact |
| **Trim** | Economist's target reached, or near a ceiling (BM price; next-cheapest substitute). Slices ≤~10–20% of a day's estimated sales, short listings |
| **Exit** | Thesis breaks (hotfix removes the level gate or adds a vendor; tier-1 supply not falling by early December, H-L2 refuted; a priced item >30% below cost for a week while supply rises). Broken floor bets: vendor (lose only the premium) or keep (costs only slots) |
| **Don't** | React to one hour (hourly prices swing a median 23% on 113) |

Judge in **real terms**: compare with a broad price basket and with "did nothing".

### 4. Questions for the owner (default in bold)
1. Which house? (a) 113 (b) 114 (c) both (d) other — **buy only where your main lives**; with characters on both, buy each item where cheaper.
2. Pot size: (a) 10% (b) **25%** (c) 50% of spare gold.
3. Bank space and a bank alt — **yes, start a bank alt** if under ~60 free slots.
4. Staging: (a) all today (b) **⅓ today, ⅓ after 11-17/18, ⅓ week of 11-30** (c) wait two weeks.
5. Priced sleeve (Pyrite, a little Pristine Leather)? (a) **yes, with the 10%-of-total-gold loss limit** (b) floor only.
6. Black Market check A before tranche 2 — **yes**.
7. Record purchases from today — **yes**.
8. Broken floor bet: **keep while slots aren't needed; vendor when they are**.

## Part 2: for the Designer, Architect and Economist

### 5. Intents for "Positions & watchlist"
Common keys: `region, house_id, world, faction, item_id, variant, snapshot_at, data_age_min, formula_version, confidence, confidence_reasons[]`.

- **W1 Floor watch.** *"Can I still buy this near what a vendor pays me back, how many, at what cost?"* Cautious holders,
  small budgets, advisors before floor buys. Compare: min and p10 vs vendor (ratio, worst-case %), units and gold under the
  player's cap, value per slot, same item on other reachable houses, floor refill since last visit. Horizon: latest hour vs
  7–14 days of the ratio. Urgency: units under cap hours, below-vendor units minutes; the ratio days. Certainty: listings
  firm but 1–2 h old; vendor price firm but hotfixable (Mild Spices cut to 1c). Action: buy only under the cap, or wait.
  Not: "cheap so it will rise" (the floor protects, it doesn't predict); "all these units are at the floor price".
  Fields: `vendor_sell, min_price, p10, ratio_min, ratio_p10, worst_case_loss_pct, cap_ratio, units_under_cap,
  gold_under_cap, cost_for_n(n), value_per_slot, stack_size, ratio_p10_7d[], floor_refill_hours_est, below_vendor_units,
  other_houses[{house_id, ratio_min, reachable}]`.
- **W2 Position ledger.** *"What do I hold, what did it cost, what is it worth (guaranteed and realistic), how far from
  floor and ceiling?"* Compare cost basis vs **vendor value** (guaranteed), **realistic value** (clearing price × 0.95,
  limited to what the house absorbs in N days) and **headline value** (cheapest listing, least reliable); distance to the
  ceiling (BM price or cheapest substitute); vs "did nothing" and a price basket; totals per sleeve and bet group; slots
  used. Horizon: life of the position, daily. Not: realised profit; nominal as real. Fields: `position_id, lots[{bought_at,
  house_id, qty, unit_cost, sleeve, cap_used, thesis_ids[]}], qty_open, cost_basis, vendor_value, value_realistic,
  value_headline, absorb_units_day_est, days_to_exit_est, pct_of_house_listed, ceiling{type, price, source, trust},
  gain_vs_cost_pct, gain_vs_basket_pct, slots_used, bet_group, realised[{sold_at, qty, net}]`.
- **W3 Thesis checks.** *"Is the reason I bought this still true?"* Each linked hypothesis (H-L1–H-L8, H-P1–H-P7) vs its
  pass/fail line and due date; status not yet testable / on track / at risk / passed / refuted; the evidence. Weekly; most
  due 12-07 to 12-31. A refutation is an exit prompt, not an emergency. Not: "on track" = "will profit". Fields:
  `thesis_id, statement, pass_rule, fail_rule, due_at, status, evidence[{metric, value, baseline, as_of}], days_of_data,
  positions_linked[]`.
- **W4 Triggers and exit plan.** *"Add, hold, trim or get out this week, and if selling, how fast?"* Low-playtime players
  need a weekly digest. Each rule set at entry vs latest data (under cap, supply trend, target, ceiling near, thesis
  refuted, stop, time limit, event ahead); for trims, slice vs daily sales and net per unit by vendor / 2 h / 8 h listing.
  Not an instruction: the player decides. Fields: `rules[{type, threshold, set_at}], fired[{rule, at, value, signal_kind}],
  slice_qty, slice_share_of_daily_sales, net_unit_vendor, net_unit_ah_2h, net_unit_ah_8h, deposit_unit_2h,
  deposit_unit_8h, cut_pct, next_event{type, at, source}`.
- **W5 Watchlist** (not held). *"Which candidates are getting more or less attractive?"* Ratio to vendor and ceiling,
  week-over-week price and units posted, pullbacks with falling supply. "Not yet established" until two weeks of data.
  Not a buy list. Fields: W1's plus `trend_dir, posted_units_wow_pct, price_wow_pct, ceiling_distance_pct`.

### 6. Data needs added to the catalog

| # | Need | Status | Priority |
|---|---|---|---|
| P1 | Vendor sell price per item | **Have** in the `market` export; not in the main pipeline (#70) | Must |
| P2 | Price-to-vendor ratio (min, p10) per house-hour | Derive | Must |
| P3 | Units/gold under X× vendor; cost to buy N | Derive (approx. from flows depth, measured from cheapest); exact needs raw — **collect now or lose**, raw from 11-14 expires **11-28** | Should |
| P4 | Sales/day and posted/day for watched items | Have in flows (`sold_est` low, #69) | Must |
| P5 | **Launch-period history kept past 90 days** (daily min/p10/median, qty, flow totals) | **Collect now or lose** — hourly and flows from 11-14 expire ~**2027-02-12**; needs #26 for every day since 11-14 | Must |
| P6 | **Position ledger** typed in by the owner | New; **collect now or lose** from the first purchase | Must |
| P7 | **Entry rationale saved at purchase**, never edited | New; collect now or lose | Must |
| P8 | Bank/bag capacity; stack size per item | New (typed in; game data) | Should |
| P9 | Scarce tier tag and dated Black Market price per item | New (game data; in-game check A monthly or after hotfixes) | Must |
| P10 | Consumers and substitutes per item; cheapest substitute as ceiling | New (wago.tools SpellReagents) + Derive | Should |
| P11 | Uses of Bauxite and Moss Agate; Sulfuric Acid recipe inputs and cooldown | New (Researcher) | Should, before tranche 2 |
| P12 | Broad price basket (inflation index) per house | Derive from the roll-up | Should |
| P13 | Event calendar (maintenance, raids 12-09, Hardcore, relevant hotfixes) | New | Must |
| P14 | Pyrite level-gate proof (check B); recipe-scroll sources (check C) | New (in game) | Should |
| P15 | Mature-economy reference: same items on Classic Era / anniversary realms, launch-glut duration | New source, **unverified** (Strategist's memory that Blizzard's API serves Classic auctions; Researcher to check) | Later |
| P16 | Player population by level band | **Can't get**; stand-in: leveling-demand index (v1 #32) | — |

**Gaps:** #26 now protects open positions and must cover every day from 11-14 before 2027-02-12; vendor price not yet in
the main pipeline (#70); flows depth is from the cheapest price, not vendor; the v1 "5-silver penny filter" would hide
Pyrite, Tigerseye, Pristine Hide (floor watch must be exempt); `sold_est` undercounts 2-hour sales (#69), a safe-side error.

**Analyst tests:**
- H-P1: listings under ~1.05× vendor are bought within hours (other accumulators present).
- H-P2: floor supply refills within 24–48 h after being bought down (staged buying works).
- H-P3: after the deposit change (US 11-17, EU 11-18), p10 of 1s-vendor items (Pyrite, Tigerseye) falls relative to
  higher-vendor items.
- H-P4: the 113–114 price gap closes over weeks (if not, house choice is a lasting edge).
- H-P5: Sulfuric Acid tracks 2 × Pyrite plus a steady spread.
- H-P6: a broad price basket rises over weeks (gold inflation).
- H-P7: tier-1 supply responds to price (one week's p10 change vs next week's units posted).

### 7. Questions for the Economist
1. What does "normalised" mean per group (classic gems, scarce tier 1, tier 2): target price, ratio to vendor or to
   substitutes; when; how sure?
2. Gold inflation: how fast; what real return must a position beat?
3. Tier-1 supply path: how fast does the share of gatherers ≤25 shrink; offset by Legacy alts and Bountiful Harvest; is
   there an **"alt-farm wage" ceiling** well below the 5g BM price?
4. Demand timing: when do crafters reach skill 200–290 in numbers; size of the 12-09 raid effect; does Hardcore matter?
5. Ceilings: is the BM a hard cap; odds Blizzard changes it or the scarce rules; do substitutes cap gems (H-L5)?
6. Exit capacity and crowding at "normal" prices.
7. Holding periods and time limits per item; when to release a non-moving floor bet.
8. Is a mature-economy reference (P15) valid for Forever?

Sources: the Researcher's report (all labels and H-L hypotheses are theirs), PLANNING (fees, deposits, volatility),
`2026-11-15-strategy-intents.md`, `2026-11-15-data-requirements-v1.md`, `collector/README.md`, `flows.py`, issues #26 #66
#69 #70 #13 #37. Worst cases, values per slot, caps and the Acid/Pyrite comparison are arithmetic on the live table.

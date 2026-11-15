# Presentation spec and first mock-ups (2026-11-15)

The Designer agent's first job (`.claude/agents/designer.md`, PonchoAndy/DayTrader#48): the Strategist's 18
intents (`docs/designs/2026-11-15-strategy-intents.md`) turned into a presentation spec and three mock-up
pages in `docs/mockups/2026-11-15-first-views/`, published at https://claude.ai/artifact/4wAUvyrpY962Guc4R6omp8.

## Review notes (main session)

- **Rendered and checked** (desktop light, phone dark): no script errors, no sideways scrolling on any page.
- **Real data checked:** Thorium Bar on 113 (17.0 s → 25.0 s at the 17:17 reset, +733 units refilled by
  18:17) matches the demo data.
- **The agent had no Edit tool**, only Write, so every fix meant rewriting a whole page; it left two small
  flaws rather than rewrite again (leader lines crossing labels in item-page's other-houses strip; a legend
  note it believed was in item-page wasn't found in the saved file). Edit has been added to its tools.
- **Resumed after a usage-limit stop**: the agent picked up from its saved state with SendMessage.

---

I've written three mock-up pages and the presentation spec for all 18 intents (S1–S10, T1–T8). The pages are the T1 deal scanner, the T2 item page for Thorium Bar on house 113, and a shared visual-language sheet that both tools follow. They are hand-written HTML and SVG with no libraries, and work at phone width and in light and dark themes. I haven't looked at them in a real browser (I had no browser or shell), so a quick look on a phone and in dark mode is still needed.

The demo data ends on 14 Nov, so every page pretends it's 19:09 UTC on 14 Nov. Prices and quantities are real house-113 data from 03:17–18:17. Sale rates, depth, clearing prices, survival odds, lock time, undercut counts, vendor prices and the verdicts are sample values. Each page has a "Sample data" banner, and every sample value carries a † or a "sample" tag.

# Part 1: For the owner

## 1. Summary
1. Every screen uses the same five markers, always drawn the same way:
   - **How fast a signal changes:** fleeting, intraday, multi-day or trend. The tag is loudest (solid ink) for fleeting.
   - **How old the data is:** counted from Blizzard's :17 snapshot. Rows turn gold after one missed refresh and grey out after two.
   - **How sure we are:** Low, Medium or High, always followed by the reasons.
   - **What could fool you:** red trap flags or gold caution flags.
   - **Certain versus probable:** always in separate sections.
2. One drawing rule carries honesty everywhere: **solid means counted, dashed or "≈ range" means estimated, hatched means missing.** Estimates are never shown as one number ("≈ 1,500–3,000 a day", never "2,214").
3. The deal scanner ranks by the **worse-case gold after fees**, at the size the deal really holds. So a big but shaky deal ranks below a steadier one, and a 1-unit bait can't top the list.
4. Traps aren't hidden. They sit in a "Looks like a deal, isn't" section, with what a naive scanner would say crossed out and the real story beside it, so a number the player saw elsewhere still makes sense.
5. While we have under 3 days of history, nothing can rise above Low–Medium confidence. The mock-ups show that state honestly instead of pretending we have a week of data.

## 2. The views
**T1 Deal scanner: "What's worth a look in my house right now?"**
- **Top of the page:**
  - A profile bar: house, budget, playtime, and a Cautious / Balanced / Bold switch.
  - A large data-age clock: "52 min since the 18:17 snapshot".
  - A short "how to read a row" key.
- **Bands, top to bottom:**
  1. **Certain** (below vendor price): one sample row. It shows a single firm profit figure but still warns "≈ 1–3 in 10 still there".
  2. **Probable** (two real rows): Grilled King Crawler Legs (1.5 s against 29 s normal) and Scroll of Imbue Precision.
  3. **Looks like a deal, isn't:** five real traps.
     - Postbox Key: bait, and no sales.
     - Crimson Lotus: falling knife.
     - Thorium Bar: a reset.
     - Essence of Fire on 114: not your house.
     - Crystal Vial: a penny item.
  4. **Cheap now for what you'd buy anyway:** Runecloth and Thick Leather, shown inside today's price range.
  5. **Gone since the last snapshot:** Arcanite Bar.
  6. The advisor hand-off as data.
- **Each probable row answers five questions:** Profit? (S1), Cheap? (S2), Sells? (S3), Holds for (S5), Still there? (S7). Each has an OK / watch / no mark plus a plain-words note.
- **Why this form:** a ranked list of answer cards rather than a wide table. Phones can't show a 10-column table, and each cell needs its own certainty treatment.

**T2 Item page: "Buy, post, wait or skip?" (Thorium Bar, 113)**
- **Verdict on top**, split by role:
  - "If you want to buy": **Wait** (multi-day; it's a reset, and buying now loses about 2–9 s a bar).
  - "If you hold some": **Post** (sell into the shortage at about 24 s, small lots; the window lasts hours).
- **Main chart:** price and supply as two panels on one time axis.
  - The 17:17 reset is marked in red, missed hours are hatched, and the line breaks across gaps.
  - A labelled sample fan projects only the supply refill.
  - No price projection, because whether resets fade (H21) isn't proven.
- **Signal cards, grouped by the question they answer:**
  - Is it cheap? S2, S9.
  - If I buy? S5, S7.
  - If I post? S4, S3, S6, S8.
  - Does it pay? S1.
  - When? S10.
  - Then other houses ("reference only", log scale) and "Can I trust this page?".
  Each card carries its own speed tag, confidence, and a real/sample badge.
- **Why grouped by question rather than S1–S10 order:** the player arrives with a question, not a signal number.

**Shared visual language page:** the reference sheet, with the rules, the four speed tiles, the three data-age states (including a stale row), the confidence and firm/estimate tables, the hazard flag table, certain versus probable, and colour roles.

## 3. Mock-ups (in docs/mockups/2026-11-15-first-views/)
- **deal-scanner.html:**
  - The Thorium Bar trap row: "+55%, buy before it climbs" is crossed out next to what actually happened.
  - The ranking note on Scroll of Imbue Precision: it has the higher expected profit but ranks 2nd.
  - The Bear Jaw line, hidden by the 0.5 g-per-trade minimum.
  - The JSON block at the bottom: what an advisor receives for row 1.
- **item-page.html:**
  - The verdict split by role, and the reset marker on the chart.
  - S6 drawn as 20 dots instead of "sells in 3.2 h".
  - S8: the "cheapest holds 10–20 min" sliver against "you're back in ~24 h".
  - S10 says "Pattern not established" instead of guessing.
  - The other-houses strip: Blackwater looks cheap but is thin.
- **visual-language.html:** the whole system on one page. This is what a builder works from.
- **Small flaws left in item-page.html** (I couldn't edit files in place and chose not to spend another full rewrite):
  - In the other-houses strip, the thin lines from labels to dots cross other labels.
  - The note under the S1 bars says "solid = worse case you'd still get". That's true for the selling row but backwards for the flip-loss row. It should read "solid = what's sure, dashed = how far the estimate stretches".
  - Fonts load from Google Fonts, as the prototype does, not from cdnjs.

## 4. Open questions for the owner
1. **Rank the scanner by worse case or by expected profit?**
   - (a) Worse case for everyone.
   - (b) Worse case for Cautious and Balanced, expected for Bold.
   - Suggested default: **(b)**.
2. **When a trap row matches, hide it or show it crossed out?**
   - (a) Always show it in the trap section.
   - (b) Show it only when a simple scanner would rank it in the top 10.
   - (c) Hide it.
   - Suggested default: **(b)**, so the section stays short.
3. **Money format.**
   - (a) Decimal gold everywhere (0.25 g).
   - (b) Coin units: one unit per comparison (25.0 s against 17.0 s), totals in gold.
   - Suggested default: **(b)**, which the mock-ups use. It is closer to how players read prices in game.
4. **Should risk level move flags between trap and caution?** For example, a falling price is a trap on Cautious and Balanced and a caution on Bold; a thin market is a trap on Cautious.
   - Suggested default: **yes**, as shown.
5. **Item-page verdict: one answer, or split by role (buyer and holder)?**
   - Suggested default: **split**. Thorium shows why: opposite answers for the same item.

# Part 2: Presentation spec

## 5. Per-signal spec table
Covered fully in mock-ups: **T1, T2, and S1–S10** (inside T2, and S1/S2/S3/S5/S7 also in T1 rows). Specified here but not mocked (deferred): **T3–T8**.

Speed key: F = fleeting, I = intraday, M = multi-day, Tr = trend.

**Signals (S1–S10)**

| Intent | Form | Time window | Comparison | Urgency | Uncertainty | Data the view needs | Hand-off to advisors |
|---|---|---|---|---|---|---|---|
| S1 Net margin | Waterfall: price → cut → deposit × relists → net. Range bar in rows, on the same scale for every row. Gold per trade, % hidden under 5 s | Now; days for exit and sell-through | Realistic exit (clearing or vendor) against entry cost; the flip case shown beside the hold/sell case | Takes the entry's speed tag | Always a range. Solid = sure part, dashed = stretch. Fee-rule confidence shown in the reason text | Clearing price, sell-through, fee rules with confidence, vendor price | S1 keys as briefed, plus `value_status` per field |
| S2 Discount + trend | Bullet graph: usual-range band, dashed normal tick, ghost dots for today's low and the morning, a red or green "now" dot | 7 d normal, 3 d short, today's hours | Cheapest and p10 against normal; 3 d against 7 d; this hour against typical for this hour | p25/p10 shift = M; cheapest only = F | Shows "trend check not available" until 3 days exist; a falling trend flips the flag | Daily p10/p25 history, hour profile | S2 keys; `trend_dir` null when not computed |
| S3 Sale rate | Range bar with the player's own quantity pinned on it; "your N ≈ x–y% of a day" | ≥7 d | Units/day against the player's planned quantity; sell-through band | M (slow) | Always "≈ range", labelled "estimated from listing changes" | Flows (sold vs cancelled), missed hours | S3 keys incl. low/high and `sale_inference_method` |
| S4 Clearing price | Stacked share bar (at cheapest / ≤5% / ≤20% / above); marker shows which band the player's price falls in | 3–7 d | Player's price on that ladder | M | Dashed segments; shows how many units it rests on | Vanished-early units by price position | S4 keys + `units_basis` |
| S5 Depth | Stepped cost ladder with the first N units shaded; chips "100 → x g"; bait check line | Latest snapshot | Cost for N against N × cheapest | F, stale at next :17 | Firm (solid) but shows the snapshot age | Units and gold within +2/5/10/25% | S5 keys |
| S7 Survival + age | In rows: 10-dot count with a hatched uncertain part, plus "listed since". On the item page: a 16-hour strip | None for the listing; weeks to calibrate | Data age + player's visit gap against typical survival | F, highest | Dot ranges; Low until calibrated | Listing first-seen times, survival curves | S7 keys + `missed_hours_in_window` |
| S6 Lock time | 20-dot count by time band, expired dots drawn hollow red; "+60 min mail" | Days | Player's hold limit, listing duration, next visit | M | Dot counts, never "3.2 h" | Listing age when it vanished, in bands | S6 keys |
| S8 Undercut | Two bars on one 24 h scale: "cheapest holds" against "you're back in"; Contested flag | Days | How long the cheapest holds against the player's visit gap | M pattern | "≈ range"; repost counts labelled as a guess | Undercut counts, hold durations | S8 keys |
| S9 Supply | Horizontal bars for the last hours against a dashed "typical" line; time-left stacked bar; Reset flag | Days | Now against typical; posted per day against sold per day | M | Counts firm; typical and rates are estimates | Hourly quantity, posted and sold per day, time-left mix | S9 keys incl. `reset_flag` |
| S10 Timing + events | 24-hour bars (faint today-only readings) with a "Pattern not established" overlay; event card with date, source trust and item relevance | 2 wk daily, 4 wk weekly | This hour against the day; days to the next event | I pattern / M event | Placeholder until established; confidence follows the source (official > news) | Weekly hour profile, forward event calendar | S10 keys + `relevance_to_item` (new) |

**Tools (T1–T8)**

| Intent | Form | Time window | Comparison | Urgency | Uncertainty | Data the view needs | Hand-off to advisors |
|---|---|---|---|---|---|---|---|
| T1 Deal scanner | Profile bar, age clock, bands: Certain / Probable / traps / restock / gone; 5-answer rows | Latest hour vs days | S1 worse case ranks; S2, S7 | Every row shows age; greyed after 2 missed refreshes | Per-row confidence with reasons; history cap | S1, S2, S3, S5, S7 + vendor prices | Rows with `class`, `hazard_flags[]`, `rank_basis`, `value_status` (shown on the page) |
| T2 Item page | Role-split verdict, two-panel chart with event and missed-hour marks, cards grouped by question | Hours / days / weeks | All signals, plus other houses as reference only | Per card | Per card; real/sample badge | S1–S10 | S1–S10 bundle, `variants[]`, `events_in_window[]`, `verdict{role, action, signal_kind, confidence}` |
| T3 Posting helper (deferred) | Price slider placed on the S4 ladder; dots "sold by your next visit"; absorption bar; net against vendor | Days + hour profile | Player's price, quantity and next visit | Low–medium | Dot ranges | S3, S4, S6, S8, S10, vendor | T3 keys as briefed |
| T4 Crafting planner (deferred) | Ranked recipe table: reagent cost against product exit, net range, sales/day, cooldown and bind badges; margin by skill as a small multiple | Days–weeks | Net per craft × absorbable volume | Slow (Tr/M tags) | Range; recipe-data confidence | Recipes, vendor prices, bind status, cooldowns (N5) | T4 keys |
| T5 Gathering planner (deferred) | Gold per hour = farm rate × net price, capped at absorption (bar with a cap line); price-impact curve for the player's volume | Days–weeks | Planned volume against daily absorption | Slow | Farm rate marked "your number"; impact marked "model" | S3, depth above cheapest, zones (game data) | T5 keys |
| T6 Cross-house / Blackwater board (deferred) | Two-sided check: buyer's saving and my net after 15%, both must pass, plus a Blackwater sales gauge; not-your-house rows shown greyed | Days | Both inequalities | M | Fee and house-link confidence; Thin flag | Reachability (#13), Blackwater flows | T6 keys |
| T7 Watchlist (deferred) | Alert cards: trigger met, value, data age, speed tag ("fleeting: may be gone") | Latest hour | Trigger against latest value | High | Inherited from the signal | Triggers, latest snapshot | T7 keys |
| T8 Journal + scorecard (deferred) | Positions: cost basis against realistic value (range), progress bar, exit-trigger chips. Scorecard: advisor against do-nothing and naive-rule baselines, with a calibration chart | Life of each position | Paper against real | Exit triggers urgent | Paper values dashed, real trades solid | Journal (N7), advice ledger (N8), baselines (N13) | T8 keys |

**Where the obvious form would mislead, and what I used instead**
- **One chart with two y-axes for price and supply:** a supply crash looks like a price move. I used two panels on one time axis.
- **A line drawn across missed hours:** it invents data. The line breaks and the gap is hatched.
- **"Sells in 3.2 h" or "62% chance":** false precision. I used dot counts with a hatched uncertain part (Kay et al. 2016).
- **% discounts on cheap items:** I used gold per trade and show no % at these prices (the Crystal Vial row, ≈ 5 s).
- **Ranking by discount:** bait and falling knives would come first. I rank by worse-case net gold.
- **A single "normal" line with a 15-hour history:** it reads as authoritative. It's drawn dashed with "15 h so far".
- **A price projection after the reset:** it implies we know resets fade. I gave only a supply fan, and said the rest in words.

## 6. Visual system
- **Reused unchanged:** all prototype tokens (bg, surface, fg, muted, line, gold, grid/axis/tick, faction colours, series, up/down, quality colours), with Sora, Inter and JetBrains Mono.
- **New tokens:**
  - `--down-soft` and `--up-soft` (12% colour-mix), for trap and certain backgrounds.
  - `--hatch` (diagonal pattern), for missing, stale and not-established states.
- **Colour roles:** one job per colour.
  - Green/red = money direction and OK/no.
  - Gold = caution and sample labels, which the prototype's `.flag` already does.
  - Purple = data series, speed tags and the probable edge.
  - Faction colours = houses only.
  - Confidence is drawn in neutral ink, never green or red.
- **Speed tags:**
  - Fleeting: solid ink with an hourglass icon.
  - Intraday: purple outline with a wave icon.
  - Multi-day: purple-soft fill with a bars icon.
  - Trend: dashed muted outline with an arrow icon.
- **Data-age states (suggested thresholds):**
  - Fresh: under 75 min after the snapshot.
  - Aging: 75–135 min, gold text, "19:17 missing".
  - Stale: 2 or more refreshes missed; row at 60% opacity, hatched, action becomes "Too old to act on".
- **Confidence:** a 3-segment meter plus reasons. "Not established" is shown as hatched segments.
  - Suggested rule: High = 7+ days and few gaps; Medium = 3–7 days, a thin market, or an unconfirmed fee; Low = under 3 days or gaps.
  - Cap at Low–Medium until 3 days of history exist.
- **Firm, estimate, missing, sample:**
  - Firm: plain number, solid line or bar.
  - Estimate: "≈ a–b" with a dotted underline; dashed outline, fan or dots in charts; at most 2 significant figures.
  - Missing: hatched.
  - Sample: † (mock-ups only).
- **Hazard flags:** red triangle = trap (row leaves the ranked list); gold circle = caution (row stays, ranked lower). Severity can move with the risk setting.
  - The brief's six: bait, falling (and "falling · cheapest only" as a caution), reset, thin, stale, penny.
  - **Proposed additions for the Strategist:** no sales, not your house, event ahead, contested.
- **Certain versus probable:** certain has a solid green edge and one number; probable has a dashed purple edge and a range. Never in the same list.

## 7. Data the views need that doesn't exist yet (for the Architect)
1. Vendor sell prices, for the certain section and the vendor floor in S1. Fetch from game data.
2. Everything in #37 / ADR 0008:
   - depth bands (S5);
   - price position of early vanishings (S4);
   - listing age bands (S6);
   - undercut counts and hold durations (S8);
   - time-left mix (S9);
   - sales kept apart from cancels (S3).
3. **Listing first-seen time per listing, served for the latest snapshot**, so a row can say "listed since 17:17". Survival curves (S7) also need this and weeks to calibrate. Today only aggregates are planned.
4. A **survival calibration table** by price band and discount depth. New derived data.
5. **The cheapest listing and the size of the biggest listing at the cheapest, per item per hour**, for the bait check. Units within 1% is in v1 row #9; the exact minimum isn't in the hourly summary.
6. A **weekly hour-of-day profile** (v1 #15), so S10 can switch from "not established" to a pattern.
7. A **forward event calendar** with source trust and an item-relevance hint (N4). `relevance_to_item` is new: for example, lot value against the deposit change.
8. **`value_status` per field** in the export (firm / estimate / short-history / rule-unconfirmed), so views and advisors can't treat a guess as a fact. New to the export format.
9. **A missed-hours list per window** in the export, for hatching and confidence reasons.
10. **Profile fields** (N6): visit gap, hold limit, minimum gold per trade, risk band. These drive ranking and flag severity.
11. **Shopping list or reagent needs** per player, for the restock band. Typed in, or from the crafting planner.
12. **Formula version per value**, so pages can say "formula changed" instead of changing silently.

## 8. Files read and sources
- **Files:**
  - `docs/designs/2026-11-15-strategy-intents.md`
  - `docs/designs/2026-11-15-data-requirements-v1.md`
  - `docs/adr/0008-analysis-layer-daily-rollup-listing-flows-versioned-metrics.md`
  - `docs/PLANNING.md` (first-night data, auction rules, house worlds)
  - `tools/data-tour/template.html` (tokens, layout)
  - `tools/overnight-demo/template.html`
  - `tools/overnight-demo/demo-data.json`: house 113 series for all 83 items; other houses for Thorium Bar and Essence of Fire.
- **Issues:** #48 with its comment (owner wants both information and visual design, and both mock-ups and specs); #11 with its comment (where-you-trade first; variants are identity).
- **Web:**
  - Kay, Kola, Hullman and Munson, "When (ish) is my bus?", CHI 2016: quantile dotplots (https://idl.uw.edu/papers/when-ish-is-my-bus).
  - Fernandes et al., CHI 2018: dotplots improve decisions (https://mucollective.northwestern.edu/project/uncertainty-bus).
  - Stephen Few, bullet graph design spec (https://www.telerik.com/docs/default-source/blogs-docs/bullet_graph_design_spec-pdf).
  - Bank of England, "understanding the fan chart" (https://www.bankofengland.co.uk/quarterly-bulletin/1998/q1/the-inflation-report-projections-understanding-the-fan-chart).
  - All read as search summaries only.

Files are in docs/mockups/2026-11-15-first-views/:
- deal-scanner.html
- item-page.html
- visual-language.html
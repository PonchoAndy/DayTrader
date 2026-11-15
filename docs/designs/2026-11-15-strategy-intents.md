# Strategy intents: the director's interview (2026-11-15)

The Strategist agent's second job (`.claude/agents/strategist.md`, PonchoAndy/DayTrader#39): what tools
DayTrader needs and what each must make clear, written as **intents** for the Designer (#48), who
decides how they look. Builds on `docs/designs/2026-11-15-data-requirements-v1.md`. **The owner can
edit this file**; the Designer works from it.

## Review notes (main session)

- **Checked against the demo data and right:** Thorium Bar's "reset" on house 113 (1,210 units →
  100 in an hour while p10 went 0.16 g → 0.25 g, refilled to 833 by 18:17), Crimson Lotus falling
  0.70 g → 0.13 g while supply rose 57 → 139, Runecloth ~7.7 → ~6 silver, Arcanite Bar 60.8 g → 7–10
  units at 45–50 g, and the Postbox Key's single 1-silver listing after hours at 1 g.
- **Checked and right:** 2026-11-17 is a Tuesday; raw pulls from 11-14 to 11-17 expire 11-28 to 12-01.
- **Sources conflict, flagged by the agent:** whether the 1-copper minimum deposit is already live
  (news, after 11-10) or arrives with maintenance on 11-17 (PLANNING, Blizzard staff post). An
  in-game check before and after Tuesday settles it (added to #13).
- **Unverified, flagged by the agent:** Crystal Vial being vendor-sold, the Arcanite transmute
  cooldown, game-table names, and the TSM sale-rate rule of thumb (0.1–0.3, community claim).
- **New "collect now or lose" item (N1):** lot size and lot value of new listings, for a before/after
  view of the deposit change. Not in ADR 0008's accepted measures; needs the owner's OK.

---


Builds on `docs/designs/2026-11-15-data-requirements-v1.md` (written "v1" below; rows are "v1 #N", hypotheses "H1–H18"). It doesn't repeat that catalog. Examples come from `docs/PLANNING.md` and the overnight demo data (`tools/overnight-demo/demo-data.json`, house 113 unless noted, hourly snapshots 2026-11-14 03:17 to 18:17 UTC).

---

## Part 1: For the owner

### 1. Summary

1. Before I recommend any trade I need three answers: **is it really profit after fees**, **will it sell at that price within the player's next visits**, and **how sure are we**. Ten signals cover those three answers. The rest are details inside them.
2. Eight tools cover every player type: a deal scanner, an item page, a posting helper, a crafting planner, a gathering planner, a cross-house and Blackwater board, a watchlist, and a trade journal with a scorecard.
3. The most urgent new item is the **minimum-deposit change expected at maintenance on Tuesday 2026-11-17**. We only have about 3½ days of "before" data. Measures of how people post (lot sizes and lot values of new listings) exist only in raw pulls, and the first of those expire around **2026-11-28**.
4. Advisors can only be compared if each piece of advice is saved, at the moment it's given, in a fixed format with the data it was based on. Advice is then scored against what the market did afterwards. Saved advice can't be rebuilt later.
5. Trust breaks fastest on four mistakes: profits that fees wipe out, deals already gone when shown, prices from a house the player can't use, and sale rates that count cancelled listings as sales.

### 2. Answers to the interview questions

#### Q1. Signals: 20 candidates, pruned to 10

**The 20 I'd look at:**
1. Discount against normal price
2. Normal price itself
3. Trend (short against long window)
4. Volatility
5. Units sold per day
6. Sell-through
7. Price at which units actually sell
8. Depth (cost to buy N units)
9. Lock time (how long until it sells)
10. Undercut frequency
11. How long a deal survives
12. Flood or shortage (current supply against typical)
13. Net margin after cut and deposit
14. Vendor floor and vendor price
15. Gap to other houses and the Blackwater bridge
16. Hour-of-day and day-of-week pattern
17. Supply concentration (a lone cheap listing, one big seller)
18. Time-left mix (supply about to expire)
19. Repost churn and "reset" signature (bots, one seller resetting the price)
20. Recipe margin, plus data confidence and event proximity

**The 10 I keep:**

| # | Signal | What it tells me | Decisions it serves | Who cares most |
|---|---|---|---|---|
| S1 | **Net margin after fees** (cut, deposit lost on each expiry, vendor floor) | Whether there is any profit at all, at the price the item really sells for | Every buy, post, craft and bridge decision | Everyone. Most of all low-budget players and anyone at Blackwater (15% cut) |
| S2 | **Discount against normal price, with a trend check** | Is it cheap, and is "cheap" holding or still falling? | Buy now, flip, restock reagents | Flippers, crafters buying reagents, risk-averse players |
| S3 | **Sale rate and sell-through** | Will it sell at all, and how many a day? | Flip, post, craft volume, farm volume | Low-playtime players, small budgets, cautious players |
| S4 | **Clearing price** (where buyers actually buy: at the cheapest, within 5%, within 20%, above) | The realistic exit price, and the price to post at | Post pricing, margin exit price, gatherers' sell price | Gatherers, crafters, anyone posting |
| S5 | **Depth and concentration** (cost to buy N; whether the cheapest is a single bait unit) | Whether the deal is real at the size I want | Buy size, cornering, bait detection | Bigger budgets, cornering, speculators |
| S6 | **Lock time** (listing age at sale) | How long my gold is tied up | Budget planning, choosing between trades | Small budgets, players who want quick turnover |
| S7 | **Deal survival and data age** | Will it still be there when the player logs in? | "Buy right now" | Low and medium playtime players |
| S8 | **Undercut pressure** (how often the cheapest spot is taken; repost churn) | Can a player with my playtime hold the cheapest spot? | Post or don't post, posting price | Once-a-day players; anyone competing with bots |
| S9 | **Supply balance** (flood or shortage, how fast new supply arrives, time-left mix) | Is supply piling up, or about to dry up? | Buy timing, cornering, sell timing, farming | Speculators, cornerers, gatherers |
| S10 | **Timing pattern and event proximity** (hour of day, day of week, maintenance or hotfix ahead) | When to buy and when to sell; whether a known shock is coming | Buy and sell hour, speculation, holding through events | Players with flexible hours, speculators |

**What got cut, and why:**
- **Volatility** isn't a headline signal. It feeds S2's trend check and the certainty of every number. A trader uses it to size positions, not to pick them.
- **The cross-house gap** is a comparison applied to S1 and S2, not a signal of its own. It becomes a tool (the cross-house board). It is only usable once #13 says which houses the player can reach.
- **Recipe margin** is S1 applied to reagents against the product. It becomes a tool (the crafting planner).
- **Vendor floor** is folded into S1. It sets the worst-case exit.
- **Concentration** is folded into S5, and the **time-left mix** into S9.
- **Repost churn and the reset signature** are folded into S8 and the hazard flags.
- **Data confidence** isn't a signal at all. It is a property every signal must carry.
- **Normal price** isn't shown on its own. It is the yardstick inside S2.

#### Q2. Simple wins for a new trader today

These are ordered by how safe they are. The app should label the first kind **certain** and the rest **probable**, and never mix the two labels.

1. **Below-vendor buys (certain).** A listing priced under the item's vendor sell price can be bought and sold straight to a vendor, with no market risk.
   - *How the app spots it:* the latest cheapest price is below the vendor sell price. Profit = vendor price minus cost, with no cut.
   - *Needs:* vendor sell prices (v1 "New", game data).
   - *Catch:* in-game snipers take these within minutes, so most will be gone before our hourly data shows them (S7). Show how long the listing has survived, and expect few hits.
2. **Selling your own loot and gathered goods better (no capital).** Compare, per item, what the auction house pays after the cut and the deposit risk with what a vendor pays. Then post at the clearing price (S4), at the best hour (S10), in amounts the market absorbs (S3).
   - *Example:* Copper and Tin Ore drained 87–89% overnight without the price moving (PLANNING), so a leveling player's ore sells.
   - *How the app spots it:* the player names the item (or later, their bags), and the posting helper answers.
3. **Buying what you need anyway, at the dip (low risk).** A crafter or leveler who will buy reagents regardless saves by buying at the day's low rather than the evening peak. There's no resale risk.
   - *Example:* Runecloth on 113 had a p10 of 7.75 silver at 03:17 and about 6 silver by 15:17–17:17. That is a ~20% swing on one day, unproven as a pattern (H7).
   - *How the app spots it:* the hour-of-day profile, plus a "today's price against typical for this hour" flag on the player's shopping list.
4. **Flipping deep commodities on a dip (probable).** Pick items with thousands of units and steady daily sales, such as Runecloth or Thorium Bar. Buy when p10 is clearly below normal **and** the trend isn't falling **and** the gap is bigger than the 5% cut plus the deposit.
   - *How the app spots it:* S2, S3 and S1 all pass; depth (S5) covers the planned size; lock time (S6) fits the player's hold limit.
5. **Vendor-goods resale (probable).** Some reagents are sold by vendors, yet players buy them on the auction house. Crystal Vial shows up in the demo's "demand" list; that it's vendor-sold is my memory, to be checked in game data.
   - *How the app spots it:* the auction price is well above vendor price plus fees, and units sold per day is steady.
   - *Catch:* this depends on vendor prices that hotfixes change (Mild Spices was cut to 1 copper).

#### Q3. Hazards and traps

| Trap | Real example | Data that exposes it | What the player must understand |
|---|---|---|---|
| **Never sells** | Ezra Grimm's Postbox Key on 113: 1–3 listed at 1 g for 11 hours, nothing moving | Sale rate near 0; sell-through low; vanishings mostly at expiry; listings piling up | A low price is no use if nobody buys. Each expiry burns the deposit. |
| **Fees eat the margin** | Any bridge trade at Blackwater: 15% cut (unconfirmed) | S1, with the deposit cost multiplied by the expected number of relists (more relists when sell-through is low) | Margin has to clear the cut, the deposit and the relist cost. On penny items the price steps are bigger than the margin. |
| **Bait, or a single mispriced unit** | Ezra's Key: one listing at 1 silver after hours at 1 g | Cheapest price far below p10; units within +2% of the cheapest = 1 | The "deal" is one unit. Buying 20 costs the normal price. |
| **One seller pushing the price up (a reset)** | Thorium Bar 113 at 17:17: units fell from about 1,200 to 100, and p10 rose from 0.16 g to 0.25 g; supply refilled to 833 by 18:17 at ~0.25 g | Quantity collapse in 1–2 hours plus a new, higher floor; few large listings at the cheapest; how fast new supply arrives | A jump with supply gone isn't demand. Buying in at the new floor is betting the reset holds. It usually lasts only until new supply arrives (H21). |
| **Falling knife** | Crimson Lotus 113: p10 0.70 g down to 0.13 g over 15 hours while units **rose** from 57 to 139 | S2's trend check (3-day against 7-day, and the intraday slope); flood ratio rising | "Below normal" means nothing if the normal price is old news. A falling price with rising supply is a flood, not a deal. |
| **Stale data** | Every hourly view. Blizzard refreshes at :17; we store it 20–110 minutes later | Snapshot time, data age, missed-hour flags (#28) | What you see is 1–2 hours old. Cheap single listings are usually gone. |
| **Bots reposting** | Players report automated buy-and-repost (PLANNING) | Undercut count per hour; hours the cheapest price holds; repost-guess count (ADR 0008); "newest listing at the same price sells first" | A once-a-day seller can't win the cheapest spot against hourly reposting. Post at the clearing price instead, or don't post. |
| **Penny % noise** | Copper moves of 0.01 g to 0.04 g read as +300% (PLANNING) | Price steps counted in copper; gold per trade, not % | A big % on a 1-copper item is meaningless. Judge in gold per trade. |
| **Mixed variants** | Archer's Cloak: 36 variants, medians 0.3–1 g | Variant key (Have) | "Of the Eagle" and "of the Bear" are different products. Never compare a cheap variant with an average of all variants. |
| **Wrong house** | Black Lotus 10 g on 114 against 12–15 g on 113 | Which houses the player can reach (#13) | A price you can't reach isn't an opportunity. |
| **Empty Blackwater** | Blackwater often lists none of the bridge items; houses 121 and 125 have about 0.4k listings | Blackwater sale rate and depth | A bridge margin with no buyers isn't a trade. |
| **Event shock** | Deposit change, expected at the 11-17 maintenance; vendor price cuts | Event log and calendar (S10) | Before an announced change, don't hold stock of items it will make cheaper to post. |
| **Sold or cancelled confusion** | Overnight drain may be mostly expiries (H16) | Sales kept apart from cancels (v1 #4–6); "estimate" labels | Our sale rate is an estimate from listing changes, not real sales records. |
| **Thin, high-value markets** | Arcanite Bar 113: 32 units at 60.8 g down to 7–10 units at 44–50 g | Depth, units sold per day, confidence | A few trades move the price. Size small. |
| **Account economy hold** | Blizzard can block auction house use for suspected gold trading [official] | None in our data | Avoid trades that look like gold transfers, such as buying from another player at absurd prices. |

#### Q4. Edge-case strategies

**Blackwater bridge (Alliance and Horde trading through the neutral house).**
- *To spot it:*
  - The other faction's home clearing price (S4 at their house).
  - My cost at home.
  - Blackwater's 15% cut and deposit.
  - Blackwater's own sale rate and depth.
  - Competing listings already at Blackwater.
  - Which Blackwater house is linked to my world. The IDs suggest triples such as (110, 113, 116); #13 confirms.
- *The decision is two inequalities that must both hold:*
  - The buyer's side: the other faction's home price minus my Blackwater price is a big enough saving to make them buy at Blackwater.
  - My side: my Blackwater price × 0.85, minus my cost and the deposit, is positive.
- *To run it safely:*
  - Test with small lots.
  - Cap stock at Blackwater's measured daily absorption.
  - Watch the other faction's home price: if they undercut at home, the bridge closes.
  - Count the trip time to the house.
  - Main risk: the bridge sells nothing (H9, H25).

**Cornering a thin market.**
- *To spot it:*
  - The gold needed to buy everything up to a target price (depth).
  - How fast new supply arrives (units posted per day).
  - Proof that the item **sold at higher prices before** (clearing-price history, not just listings).
  - Expected resale time.
  - Signs that someone else is already cornering it (the reset signature).
- *Example:* Arcanite Bar on 113, 7–10 units at 44–50 g, is the shape of market where this is possible.
- *To run it safely:*
  - Set a maximum amount of gold before starting.
  - Stop if new supply arrives faster than it sells.
  - Plan to sell out below the peak.
  - Count the deposit on every relist.

**Speculating on game updates (the deposit change expected on Tuesday 2026-11-17).**
- *Expected effect (a belief, H19):* items whose whole listing is worth less than 1 silver become cheap to post. Expect more listings of low-value goods, lower prices for them, and more undercut churn, because reposting gets cheaper for bots too.
- *To see it:* a clean "before" baseline of how many new listings appear per hour, their lot size and lot value, undercut counts and cancel-and-repost churn, compared at the same hours of day before and after.
- *Conflict in the sources:* news coverage says the change went live with realm restarts after 11-10. PLANNING's later research says it was pulled and is due on 11-17. **The owner should note the actual deposit on a cheap item in game before Tuesday's maintenance and again after it.** Otherwise we can't tell whether there was an event at all.
- *To run it safely:* don't hold stock of penny-value goods into the change. This is mainly a learning opportunity, not a big profit.

**Reset-day patterns.**
- *What to see:* supply and price by day of week and by hours around the weekly maintenance.
  - Forever was expected to join the Tuesday maintenance schedule (a pre-launch prediction, Blizzard Watch). 11-17 is a Tuesday.
  - Demand for consumables may rise ahead of raid nights (guide claim, Engadget 2012, retail).
  - Whether maintenance cancels or keeps listings is a one-time check of listing IDs across 11-17 (H30).
- *How much data is needed:* at least 4 weeks to read a weekly pattern, so not before about **2026-12-12** (data starts 11-14).
- *To run it safely:* until then, show the pattern as "not yet established".

**Gathering for profit (#47).**
- *To spot it:*
  - The clearing price (S4) net of the cut, against the vendor floor.
  - How much the market absorbs per day (S3).
  - How far the price drops if I add 200 units (depth above the cheapest, plus refill rate).
  - The best hour to sell (S10).
  - Where it's gathered, at what level and skill (game data).
  - The player's own farm rate, which they type in.
- Gold per hour = their rate × net price, but only up to what the market absorbs.
- *To run it safely:*
  - Spread sales over days.
  - Never post more than a set share of daily absorption at once.
  - Show "you'd be X% of this market's daily sales".

**Also real:**
- **Cooldown-limited crafts.** Example: Arcanite Bar, made by an Alchemy transmute with a cooldown (my memory, check in game tables). Supply is capped, so these products are steadier.
- **Variant mispricing:** a valuable variant listed at the base item's price.
- **Shifts in leveling demand:** quest items such as Scorpok Pincer and Un'Goro Soil, and materials like Copper Ore, lose demand as players level past them (H11, H29).

#### Q5. Urgent against slow

There are four speeds. Each needs different freshness, and each goes stale differently.

| Kind | Example | Lasts | Freshness needed | Goes stale | History needed to read it |
|---|---|---|---|---|---|
| **Fleeting** (single listings) | One-unit dips like Ezra's Key at 1 silver; below-vendor listings | Minutes to a few hours | Latest snapshot; show its age | At the next :17 refresh. Acting late: it's gone, no harm except wasted time | None for the price; days for the normal price it's judged against |
| **Intraday** (daily cycle) | Runecloth evening price against morning price; supply drains about 30% by 15:00 UTC | A few hours each day, repeating | Hourly | The pattern lasts for weeks, but each day's window is a few hours. Acting late: buying at the peak | At least 2 weeks of hours (from about 11-28) |
| **Multi-day** (floods, resets, events) | Crimson Lotus flood; Thorium Bar reset; the 11-17 deposit change | 1–5 days | Daily, plus the latest hour as a check | In 1–3 days. Acting late: buying the top of a reset, or the middle of a falling knife | Days |
| **Trend** (weeks) | Leveling-material demand fading; profession margins | Weeks | Daily, or weekly | In weeks. Acting late: the profession you levelled is crowded | At least 3–4 weeks |

**How to tell them apart (rules for the app, to be proven by H22):**
- The cheapest price moves but p10 and p25 don't: **fleeting**.
- p10 moves but returns at the same hour on other days: **intraday**.
- p25 and the median move with a supply change that lasts across 2 or more days: **multi-day**.
- The 3-day normal price drifts away from the 7-day one, and sale rates change too: **trend**.

Every signal should carry its kind, so the player knows whether to act now or watch.

#### Q6. Following a strategy over time

**What the player needs to see:**
- **Gold tied up** (cost basis).
- **What the position is worth today**, valued at what it would realistically sell for: the clearing price net of the cut, limited by depth. Not the cheapest listing.
- **Progress against the plan:** units sold of the total, days held against expected lock time.
- **Exit triggers**, set at the start:
  - a stop price;
  - a time stop;
  - "supply is refilling faster than it sells";
  - an event ahead.

**The minimum data per trade:**
- Date and time.
- House.
- Item and variant.
- Action: bought, posted, sold, cancelled or expired.
- Quantity.
- Unit price.
- Deposit paid, if posted.

Buys and sales alone, typed in, are enough to start. For example: "bought 200 Thorium Bar at 0.16 g on 113", then "sold 150 at 0.24 g".

**Where it can come from:**
1. **Typed in** (now). A fast form; the sale mail gives the numbers.
2. **Matched in our data** (soon; needs testing). The player says "posted 20 at 2.10 g at 20:00". The app finds that listing in the next snapshot by item, quantity, price and time. From then on it can say whether the listing is still up, undercut, gone early (probably sold) or expired. This is advisory only, since it reads public data (H24).
3. **An in-game addon** (later, Path B). It records the player's own auction events to its saved file, the same way TSM's accounting module does. It only records; it takes no actions.

#### Q7. The toolset

1. **Deal scanner.** "What's worth a look in my house right now?" A ranked list filtered by the player's profile. Each row must make clear:
   - the net margin;
   - whether it's certain or probable;
   - how old the data is and whether the deal is likely to survive;
   - the sale rate;
   - the size the deal holds for.
2. **Item page.** "Tell me everything about this item where I trade." It must make clear:
   - normal price and trend;
   - the daily cycle;
   - depth;
   - sale rate and clearing price;
   - undercut pressure;
   - other houses;
   - events;
   - confidence.
3. **Posting helper.** "What price, when, and how many?" For sellers, gatherers and crafters. It must make clear:
   - the clearing price;
   - the chance of selling within the player's visit interval;
   - the undercut risk;
   - how much the market absorbs;
   - net proceeds against the vendor.
4. **Crafting planner.** "What should I craft, and which profession should I level?" It must make clear:
   - reagent cost at today's prices (or vendor price) against the product's clearing price, net;
   - the product's sale rate;
   - cooldowns;
   - whether the product can be traded at all (bind status);
   - margin by skill level.
5. **Gathering planner (#47).** "What should I farm, and how much should I sell?" It must make clear:
   - net price against the vendor floor;
   - daily absorption;
   - the price impact of the player's own volume;
   - the best hour;
   - zone and level;
   - gold per hour from the player's own farm rate.
6. **Cross-house and Blackwater board.** "Can I profit by moving goods between houses?" It must make clear:
   - both sides of the bridge inequality;
   - Blackwater's sale rate;
   - fees;
   - reachability.
7. **Watchlist and alerts.** "Tell me when my item hits my price or my conditions change." It must make clear the trigger met, the data age, and whether the trigger is fleeting or lasting.
8. **Trade journal and scorecard.** "How are my trades going, and whose advice worked?" It must make clear:
   - gold tied up;
   - realistic value;
   - progress;
   - exit triggers;
   - realised profit;
   - each advisor's record.

Data trust (age, gaps, confidence) and the event calendar aren't tools. Every tool shows them.

#### Q8. What the advisors need

**Input:**
- **The player profile:**
  - faction, world and the houses they can reach;
  - professions with skill;
  - level;
  - gold available;
  - the longest they'll leave gold tied up;
  - playtime (visits per day and usual hours);
  - risk band (largest loss per trade, largest share of budget in one item, hold horizon).
- **The same signal data the views use**, with snapshot time and formula version.
- **Fee rules**, with how confident we are in each.
- **The event calendar.**
- **The player's positions** from the journal.

**Output** (a fixed format so advisors can be compared):
- a recommendation ID;
- advisor;
- time;
- data snapshot and formula version;
- house;
- item and variant;
- action (buy, post, craft, farm, hold, sell, avoid, or **no trade**);
- quantity;
- limit price;
- target exit price;
- expected net profit per unit and in total;
- gold needed;
- expected lock time;
- how long the advice stays valid;
- confidence;
- named risks;
- exit rules;
- the signals behind it;
- what would change its mind.

**Keeping score:**
- Every recommendation is saved before the outcome is known and is never edited.
- **Paper score**, for all advice:
  - Was the entry price still there in the next snapshot?
  - What could realistically be sold at the end of the horizon: the clearing price net of fees, discounted by sell-through?
- **Real score**, when the player logged the trade.

**Measures:**
- Net return on gold tied up, per day.
- Hit rate.
- Calibration: did "70% confident" calls come good about 70% of the time?
- Worst loss.
- Comparison against two baselines: **do nothing**, and **the naive rule** "buy at 70% or less of normal, sell at normal".

Advisors are scored within the profile they serve. A once-a-day advisor isn't judged on hourly flips.

#### Q9. Trust: mistakes that would make a real trader quit

1. A profit that fees wipe out (wrong cut, deposit or relist cost).
2. A deal shown as current that was gone hours ago; stale data shown without its age.
3. A price from a house the player can't use.
4. Variants mixed up.
5. A one-unit bait or a falling knife sold as a deal.
6. A sale rate that counts cancelled listings as sales, leaving the player stuck with stock.
7. False precision ("sells in 3.2 hours") on estimates from thin markets or gap-ridden days.
8. Advice that changes silently when a formula changes; advisors that contradict each other with no reason given.
9. Missing an announced event (11-17) or a hotfix that changed vendor prices.
10. Advice that crowds itself: if many users are told the same flip on the same house, it stops working. This matters once DayTrader has more than one user.
11. Anything that looks like automating in-game actions, or advice that risks an economy hold.

### 3. Open questions for the owner

1. **The deposit check before Tuesday.** Before the maintenance on 2026-11-17, post one cheap item and note the deposit; repeat after. It takes 5 minutes and tells us whether 11-17 is an event at all.
   - Options: (a) do it; (b) skip it.
   - **Suggested default: (a).**
2. **Trade journal: start now, or wait for an addon?**
   - Options: (a) typed in now, minimal fields; (b) wait for Path B.
   - **Suggested default: (a).** The addon can come later.
3. **How advice is scored.**
   - Options: (a) paper only; (b) real only; (c) both, side by side.
   - **Suggested default: (c).** Paper on everything, real when the journal has the trade.
4. **Should "certain" plays (below vendor) be shown apart from "probable" ones?**
   - **Suggested default: yes, always separate.**
5. **Which advisors first?**
   - Options: (a) one; (b) two personas (a cautious banker and a speculative goblin, as in #14) plus the naive-rule baseline; (c) many.
   - **Suggested default: (b).**
6. **Deals older than one refresh.**
   - Options: (a) hide them; (b) show them with age and survival odds; (c) show them plainly.
   - **Suggested default: (b).** Grey them out after two missed refreshes.
7. **Crowding, when there are several users.**
   - Options: (a) ignore it; (b) count how many users saw each recommendation; (c) also limit how many see the same one.
   - **Suggested default: (b)** once there is more than one user. Not needed now.
8. **Reachable houses until #13 answers.**
   - **Suggested default:** one world (an Alliance, Horde, Blackwater triple, such as 110, 113, 116), with others shown as "reference only".
9. **Speculation for cautious profiles.**
   - Options: (a) hide multi-day holds from cautious profiles; (b) show them with warnings.
   - **Suggested default: (a).** The profile decides.

---

## Part 2: Intent list for the Designer

**Shorthand used in the hand-off fields:**
- **Common keys:** `house_id, faction, world, item_id, variant, kind (auction|commodity), snapshot_at, data_age_min, formula_version, confidence (0–1), confidence_reasons[]`.
- **Signal kind:** `signal_kind ∈ {fleeting, intraday, multiday, trend}` (Q5).

### Signals

#### S1. Net margin after fees
- **Decision:** "If I do this, do I actually make money?"
- **Who:** everyone. Hits hardest at Blackwater (15% cut), on small budgets, on low-sell-through items (repeated deposits) and on penny items.
- **Comparison that matters:**
  - Realistic exit (clearing price S4, or vendor price if higher) × (1 − cut).
  - Against entry cost plus deposit × expected listings per sale.
  - Shown in gold per trade, not only %.
- **Time:** the moment of the decision. Needs days of history for the clearing price and sell-through.
- **Urgency:** inherits the entry's urgency. The margin itself changes slowly.
- **Certainty:**
  - Cut and deposit are unconfirmed until #13.
  - The exit price and sell-through are estimates.
  - Show a range (pessimistic to expected), never a single exact figure.
  - The fee rule's own confidence is shown.
- **Action:** go to the buy, post or craft step with the quantity that keeps the margin positive.
- **Must not be misread as:** guaranteed profit, or a profit at the cheapest listing price. Cost of the misreading: real losses, and lost trust (Q9 #1).
- **Advisor hand-off:** `entry_cost_unit, exit_price_expected, exit_price_pessimistic, exit_basis (clearing|vendor), cut_pct, cut_confidence, deposit_unit, expected_relists, net_unit_expected, net_unit_pessimistic, net_total, qty_basis`.

#### S2. Discount against normal price, with trend check
- **Decision:** "Is this cheap, and will it stay cheap or keep falling?"
- **Who:** flippers, reagent buyers, cautious players (avoid falling knives), speculators (who want the falling ones).
- **Comparison that matters:**
  - The latest cheapest price and p10 against the normal price.
  - The 3-day normal against the 7-day normal.
  - Today's price at this hour against the typical price at this hour.
- **Time:** about a 7-day window for normal, 3 days for the short window, plus today's hours. Fewer than 3 days of history means low confidence. Our data starts 11-14.
- **Urgency:** a dip in the cheapest price only is fleeting; a p10 or p25 shift lasts days. Acting late on a dip: it's gone. Acting late on a trend: the move is over.
- **Certainty:**
  - Missed hours, thin markets and launch-era drift all weaken it.
  - The normal price lags in a trending market.
  - Example: Crimson Lotus at "18% of normal" was simply falling.
- **Action:** check depth (S5) and sale rate (S3), then buy.
- **Must not be misread as:** "below normal means it will come back up". Cost: buying a falling knife.
- **Advisor hand-off:** `min_price, p10, normal_price, normal_days, normal_short, trend_dir (up|flat|down), trend_strength, discount_min_pct, discount_p10_pct, hour_typical_p10, signal_kind`.

#### S3. Sale rate and sell-through
- **Decision:** "Will it sell, and how many can the market take a day?"
- **Who:** low-playtime and small-budget players, gatherers (absorption), crafters (volume).
- **Comparison that matters:**
  - Units sold per day against the units the player plans to sell.
  - Sell-through against a "sells reasonably" band. The community uses roughly 0.1–0.3 for TSM's sale rate (community forum and addon claims, not official TSM guidance).
- **Time:** days to weeks. At least 7 days to trust it. Flows only exist from 11-14 on.
- **Urgency:** slow. Stale after days. Acting late costs little.
- **Certainty:**
  - It's an estimate from listing changes. Cancels can look like sales.
  - Missed hours cause undercounting.
  - Always label it an estimate. Show a range on thin items.
- **Action:** size the trade to what the market absorbs; skip items with near-zero sales.
- **Must not be misread as:** confirmed sales records (TSM's come from players' own sales; ours are inferred). Cost: overstocking.
- **Advisor hand-off:** `units_sold_day_est, units_sold_day_low, units_sold_day_high, sell_through_est, days_covered, missed_hours, sale_inference_method`.

#### S4. Clearing price
- **Decision:** "At what price do buyers actually buy, so what should I post at, and what will I really get?"
- **Who:** anyone posting: gatherers, crafters, flippers on the way out. Once-a-day players need to know whether posting above the cheapest ever sells.
- **Comparison that matters:**
  - The share of early vanishings at the cheapest, within 5%, within 20% and above, against the previous hour's cheapest.
  - The player's intended price placed on that ladder.
- **Time:** days. At least 3–7 days per item.
- **Urgency:** slow; stale in days. Acting late costs little.
- **Certainty:**
  - It depends on telling sales from cancels (H3, H4).
  - Very uncertain on thin items. Show how many units the estimate rests on.
- **Action:** set the posting price; feed S1's exit price.
- **Must not be misread as:** "the price I'll get for everything I post". It's where past units cleared, at past volumes.
- **Advisor hand-off:** `share_at_min, share_within_5, share_within_20, share_above, units_basis, clearing_price_est, position_of_player_price`.

#### S5. Depth and concentration
- **Decision:** "Can I buy as many as I want at this price, or is the cheap one a single bait unit?"
- **Who:** bigger budgets, cornerers, bulk reagent buyers. Small budgets care about the bait check.
- **Comparison that matters:**
  - The cost to buy N units against N × the cheapest price.
  - Units within +2% of the cheapest.
  - The cheapest against p10.
  - The gold needed to clear the market up to a target price.
- **Time:** the latest snapshot only. History shows whether depth refills.
- **Urgency:** hourly; stale at the next refresh.
- **Certainty:** firm for the snapshot (it's listings, not estimates), but already 1–2 hours old.
- **Action:** pick the quantity and the highest price to pay; for cornering, the gold to commit.
- **Must not be misread as:** "this depth will still be there". Others buy too.
- **Advisor hand-off:** `units_within_2, units_within_5, units_within_10, units_within_25, gold_within_*, cost_for_n(n), min_vs_p10_ratio, lone_cheapest (bool), largest_listing_at_min`.

#### S6. Lock time
- **Decision:** "How long will my gold be stuck?"
- **Who:** small budgets, players with a hold limit, flippers turning gold over quickly.
- **Comparison that matters:**
  - The hours from posting to sale, in bands, against the player's longest acceptable lock.
  - Against the listing duration (a sale has to happen before expiry).
  - Against the next planned visit.
- **Time:** days of history. It needs first-seen times carried across days.
- **Urgency:** slow.
- **Certainty:**
  - An estimate. Thin items have few observations.
  - Sale gold arrives about 60 minutes after the sale for stackables, which adds to the lock time.
- **Action:** choose between trades; set a time stop.
- **Must not be misread as:** a promise.
- **Advisor hand-off:** `lock_hours_median, lock_band_shares{<2,2–12,12–24,24–48}, mail_delay_min, listing_duration_options`.

#### S7. Deal survival and data age
- **Decision:** "Will this still be there when I get to the auction house?"
- **Who:** low and medium playtime players; anyone acting on the deal scanner.
- **Comparison that matters:**
  - Data age plus the player's travel and login time, against the typical survival of similar deals.
  - How long this listing has already survived.
- **Time:** none for the listing itself; weeks to calibrate survival curves.
- **Urgency:** highest. Stale at the next :17 refresh. Acting late costs a wasted trip.
- **Certainty:**
  - Survival odds are statistical.
  - If an hour was missed, the listing's history has a hole.
- **Action:** go now, or skip.
- **Must not be misread as:** the listing is still up. Cost: frustration, and lost trust.
- **Advisor hand-off:** `snapshot_at, data_age_min, next_refresh_at, listing_first_seen, hours_survived, survival_p_2h, survival_p_6h, signal_kind`.

#### S8. Undercut pressure
- **Decision:** "If I post, will I stay the cheapest long enough to sell, given how often I log in?"
- **Who:** once-a-day players; anyone on busy commodities where bots repost.
- **Comparison that matters:**
  - The hours the cheapest price holds against the player's visit interval.
  - Undercuts per hour.
  - Repost churn.
- **Time:** days.
- **Urgency:** slow pattern.
- **Certainty:** an estimate, since repost detection is a guess.
- **Action:** post at the clearing price instead, choose a less contested item, or post at a quiet hour.
- **Must not be misread as:** "I must undercut". Undercutting into a crowded spot races the price down.
- **Advisor hand-off:** `undercuts_per_hour, cheapest_hold_hours_median, repost_ratio, price_step (copper|silver for gear), contested (bool)`.

#### S9. Supply balance
- **Decision:** "Is supply piling up or running out?"
- **Who:** speculators, cornerers, gatherers (choosing when to sell), buyers timing a dip.
- **Comparison that matters:**
  - Units listed now against typical units.
  - New units posted per day against units sold per day.
  - The share of supply about to expire.
- **Time:** days.
- **Urgency:** days. Acting late on a shortage: the price has already risen.
- **Certainty:** good for quantities; estimate-level for posting and sale rates.
- **Action:** buy into a flood (only if the trend check is stable), sell into a shortage, hold off farming.
- **Must not be misread as:** demand. A shortage after one seller bought everything is a reset (Thorium Bar, 17:17).
- **Advisor hand-off:** `qty_now, qty_typical, flood_ratio, posted_units_day, sold_units_day_est, refill_ratio, share_short_time_left, reset_flag`.

#### S10. Timing pattern and event proximity
- **Decision:** "When should I buy or sell today, and is something about to change the market?"
- **Who:** players with flexible hours; speculators; anyone holding stock through maintenance.
- **Comparison that matters:**
  - This hour's typical price and sales against the day's average.
  - Days to the next known event.
  - Before against after a past event.
- **Time:**
  - At least 2 weeks for the daily cycle (from about 11-28).
  - At least 4 weeks for the weekly cycle (from about 12-12).
  - Event comparisons need a clean "before" window.
- **Urgency:** the pattern is slow; each day's window is short.
- **Certainty:** "not yet established" until there's enough history. Events listed from official posts rate higher than news.
- **Action:** schedule buys and posts; avoid holding into a shock.
- **Must not be misread as:** a guaranteed cycle. Retail-era guide claims don't transfer automatically.
- **Advisor hand-off:** `hour_profile[24] (p10, units_sold), dow_profile[7], weeks_covered, pattern_established (bool), next_event{type, at, source, trust}, last_event{type, at}`.

### Tools

#### T1. Deal scanner
- **Decision:** "What's worth a look in my house right now?"
- **Who:** all players. The profile filters it: house, budget, playtime and risk.
- **Comparison that matters:** S1 net margin, ranked; S2 discount; S7 survival. Certain and probable plays kept apart.
- **Time:** the latest hour, judged against days of history.
- **Urgency:** highest. Each row must show its age.
- **Certainty:** every row carries confidence and its reasons, such as "3 days of history" or "thin market".
- **Action:** open the item page, or go buy.
- **Must not be misread as:** a buy list. It's a short list to check.
- **Advisor hand-off:** a list of rows with the keys from S1, S2, S3, S5 and S7, plus a `class (certain|probable)` field and a `hazard_flags[]` field (bait, falling, reset, thin, stale, penny).

#### T2. Item page
- **Decision:** "What's really going on with this item where I trade?"
- **Who:** everyone. The level of detail depends on the player's risk appetite.
- **Comparison that matters:** all ten signals for one item in one house, plus reference prices from other houses.
- **Time:** hours (today), days (normal price) and weeks (trend).
- **Urgency:** mixed. Each part shows its own signal kind.
- **Certainty:** per part. Events are marked on the history.
- **Action:** buy, post, watch or skip.
- **Must not be misread as:** "another house's price is my price".
- **Advisor hand-off:** S1–S10 bundled for the item, plus `variants[]` and `events_in_window[]`.

#### T3. Posting helper
- **Decision:** "What price, when, and how many should I post?"
- **Who:** gatherers, crafters, flippers selling, low-playtime sellers.
- **Comparison that matters:**
  - The player's price on the clearing-price ladder (S4).
  - The chance of selling before their next visit (S6, S8).
  - Net proceeds against the vendor (S1).
  - The player's quantity against daily absorption (S3).
- **Time:** days of history, plus the hour profile.
- **Urgency:** low to medium.
- **Certainty:** probabilities shown as ranges.
- **Action:** post at the suggested price and hour, or vendor the item.
- **Must not be misread as:** "this price is guaranteed to sell everything".
- **Advisor hand-off:** `suggested_price, p_sell_by_next_visit, max_qty_per_day, best_hour, net_vs_vendor`.

#### T4. Crafting planner
- **Decision:** "What should I craft, and which profession should I level?"
- **Who:** players with professions, by skill level; budget limits reagent buying.
- **Comparison that matters:**
  - Reagent cost (auction or vendor, whichever is cheaper) against the product's clearing price, net.
  - The product's sale rate.
  - Cooldowns.
  - Bind status.
- **Time:** days to weeks.
- **Urgency:** slow.
- **Certainty:** depends on recipe data quality and on the uncertainty of the product's sale rate.
- **Action:** buy reagents (at the dip, S10), craft, post via T3.
- **Must not be misread as:** "every craft I make sells at this margin". Absorption limits it.
- **Advisor hand-off:** `recipe_id, profession, skill_req, reagents[{item, qty, cost_source, unit_cost}], product_qty, net_margin_unit, product_units_sold_day, cooldown_h, tradable (bool)`.

#### T5. Gathering planner (#47)
- **Decision:** "What should I farm, where, and how much should I sell?"
- **Who:** gatherers, levelers, low-budget players (no capital needed).
- **Comparison that matters:**
  - Net price against the vendor floor.
  - Daily absorption against the player's planned volume.
  - The price drop from adding their units.
  - Gold per hour from the player's own rate.
- **Time:** days to weeks, plus the hour profile.
- **Urgency:** slow.
- **Certainty:** the farm rate is the player's own number; price impact is a model.
- **Action:** go farm in a zone, then sell through T3.
- **Must not be misread as:** "farm without limit". Their own volume crashes the price.
- **Advisor hand-off:** `item, zone[], level_req, skill_req, net_price, absorb_units_day, impact_per_100, player_rate_per_h, gph_est, share_of_market`.

#### T6. Cross-house and Blackwater board
- **Decision:** "Can I profit by moving goods between houses or factions?"
- **Who:** faction and house choice; it needs reachability (#13); budget and playtime (the trip).
- **Comparison that matters:**
  - The two-sided bridge test: the buyer's saving against their home price, and my net after 15%.
  - Blackwater's sale rate and depth.
- **Time:** days.
- **Urgency:** medium. Gaps can close within a day.
- **Certainty:** the fees and the house links are unconfirmed; Blackwater markets are thin.
- **Action:** buy at home and list at Blackwater, in small lots.
- **Must not be misread as:** "a price gap is a trade". Without Blackwater buyers it's nothing.
- **Advisor hand-off:** `home_house, bridge_house, other_home_house, my_cost, other_home_clearing, my_bw_price, buyer_saving, my_net, bw_units_sold_day, bw_depth, reachable (bool), fee_confidence`.

#### T7. Watchlist and alerts
- **Decision:** "Tell me when my item reaches my price or my situation changes."
- **Who:** low-playtime players especially, and anyone holding positions.
- **Comparison that matters:** the player's trigger (price, supply, event, an undercut on their own listing) against the latest data.
- **Time:** the latest hour.
- **Urgency:** high. An alert must say how old it is and whether it's fleeting.
- **Certainty:** inherited from the signal that fired.
- **Action:** go to the item page or the journal.
- **Must not be misread as:** a real-time feed. It's at best hourly.
- **Advisor hand-off:** `trigger{type, threshold}, fired_at, snapshot_at, value_at_fire, signal_kind`.

#### T8. Trade journal and scorecard
- **Decision:** "How are my trades doing, when do I get out, and whose advice worked?"
- **Who:** anyone with positions; advisors' scoring.
- **Comparison that matters:**
  - Cost basis against realistic value.
  - Progress against plan.
  - Exit triggers.
  - Realised profit against paper profit.
  - Each advisor against the do-nothing and naive-rule baselines.
- **Time:** the life of each position, in days to weeks.
- **Urgency:** exit triggers are urgent; the score is slow.
- **Certainty:** real trades are firm; paper outcomes and realistic values are estimates.
- **Action:** hold, sell, cut losses; choose which advisor to follow.
- **Must not be misread as:** the paper score being real profit.
- **Advisor hand-off:** `position{trade_ids[], qty_open, cost_basis, value_realistic, days_held, exit_rules[]}`, `recommendation{rec_id, advisor, created_at, data_snapshot, formula_version, …(Q8 fields)}`, `outcome{paper_net, real_net, hit (bool), horizon_end}`.

---

## Part 3: Data still missing, hypotheses, sources

### Data still missing (not in the v1 catalog)

| # | Need | Status | Why | Priority |
|---|---|---|---|---|
| N1 | **Lot size and lot value of new listings** per item per hour, in bands (for example, total listing value under 1 silver, 1–10 silver, …) | **Collect now or lose** (raw only). The days before 11-17 expire from **about 2026-11-28 to 2026-12-01** | It's the cleanest "before" baseline for the deposit change (H19), and lot splitting shows how undercutting behaves. Not in ADR 0008's accepted measures. | Must |
| N2 | **Deposit in game before and after 11-17** (the owner checks a cheap item) | New (in game); **before Tuesday's maintenance** | Sources conflict on whether the change is already live | Must |
| N3 | **The exact maintenance time on 11-17**, and whether listings survive it | Event log (official); the listing-ID check needs raw from 11-17, which expires about **2026-12-01** | Event study; reset-day pattern (H30) | Must |
| N4 | **Forward calendar** of announced maintenance, hotfixes and phases | New (Blizzard posts, official) | Speculation and "event ahead" warnings; v1 only logged past events | Should |
| N5 | **Recipe cooldowns, item bind status, maximum stack size, items used by quests** | New (Forever game tables on wago.tools). Table names are from my memory and need checking | Crafting supply caps, whether products can be sold, lots for deposit, quest-item demand | Should |
| N6 | **Player profile**: reachable houses, professions and skill, level, gold, longest lock, visit pattern, risk band | New (typed in) | Every advisor input | Must (when the app exists) |
| N7 | **Trade journal**, minimum fields as in Q6 | New (typed in now; addon later) | Position tracking, real scoring | Should |
| N8 | **Advice ledger**: every recommendation, fixed fields, saved before the outcome | **Collect now or lose** from the day advisors run. It can't be rebuilt | Comparing advisors | Must (with the advisors) |
| N9 | **Advice exposure count**: how many users saw each recommendation | New (internal) | Crowding (Q9 #10) | Later |
| N10 | **Matching the player's own listing** in public data from item, quantity, price and time | Derive (test H24) | Journal without an addon; alerts on the player's own listings | Should |
| N11 | **Price-step rule per item class** (gear in whole silver) | Have (rule in PLANNING plus item class) | Undercut and penny-noise math | Should |
| N12 | **Sale-gold delay** (about 60 minutes, stackables) as part of lock time | Have (rule) | Gold turnover for fast flippers | Should |
| N13 | **Baseline outcomes** (the naive 70% rule; do nothing) | Derive from daily and hourly data | Scoring needs a yardstick | Should |
| N14 | **Player's bags and bank** | Can't via the API. Stand-in: typed in, or the addon later | "What should I do with what I have" | Later |

### Hypotheses for the Analyst (they continue from v1's H1–H18)

| # | Claim | Test | Deadline |
|---|---|---|---|
| H19 | The deposit change raises the number of new listings with lot value under 1 silver and lowers p10 for low-value items | Before and after 11-17, same hours of day, by lot-value band (N1). Weak with only 3½ days before; say so | Raw before about **11-28** |
| H20 | A falling price with rising supply (Crimson Lotus) keeps falling the next day more often than it recovers | Next-day p10 change, given a one-day fall and a rising flood ratio, across items | Weeks of daily data |
| H21 | A "reset" (supply down more than 80% within 2 hours, p10 up more than 30%; Thorium Bar 113 at 17:17) reverts within 1–3 days | Find such events; track p10 at 24 and 72 hours | Raw or hourly data, ongoing |
| H22 | Moves in only the cheapest price revert within hours; moves in p25 last for days | Autocorrelation of each discount measure at 1, 6, 24 and 72 hours | 2 or more weeks of hourly data |
| H23 | A listing at the clearing price sells within 12 or 24 hours with a stable, measurable probability | Flows: the share of new listings, by price position, that vanished early within 12 and 24 hours | Raw before about 11-28 for the earliest days |
| H24 | A player's own listing can be found in the next snapshot from item, quantity, price and time | The owner posts 3 listings and notes the details; match them | Any time |
| H25 | Blackwater listings sell to the other faction when priced below that faction's home p10 | Blackwater early-vanishing rate against price relative to the other faction's home p10 | Flows, weeks |
| H26 | Paper scores roughly track real outcomes | Compare them once journal entries exist | Later |
| H27 | Demand for quest items (Scorpok Pincer, Un'Goro Soil, Okra) moves with the population's level curve | Trend in daily sale rate against level bands; quest-use data (N5) | 4–8 weeks |
| H28 | The naive rule "buy at 70% or less of normal" beats doing nothing after fees, on deep commodities (this is v1's H6 reframed as the advisor baseline) | Paper backtest, net of a 5% cut and the deposit, with sell-through applied | 2 or more weeks |
| H29 | Weekly maintenance keeps listings (IDs carry over) rather than cancelling them | Listing IDs just before and after the 11-17 maintenance | Raw before about **12-01** |

### Sources and files read

**Files:**
- `CLAUDE.md`
- `docs/designs/2026-11-15-data-requirements-v1.md`
- `docs/PLANNING.md` (§1 including "TSM's numbers and WoW Forever's auction rules", §3, §5)
- `docs/adr/0008-analysis-layer-daily-rollup-listing-flows-versioned-metrics.md`
- `docs/designs/2026-11-14-analysis-layer.md` (by search)
- `collector/README.md`
- `docs/sessions/2026-11-14.md`, `docs/sessions/2026-11-15.md`
- `.claude/agents/designer.md`
- `tools/overnight-demo/demo-data.json`: Black Lotus, Thorium Bar, Runecloth, Arcanite Bar, Crimson Lotus, Red Whelp Scale, Ezra Grimm's Postbox Key; snapshot times.

**Issues:** #11 (1 comment), #13 (3 comments), #14 (1 comment), #46 (no comments), #47 (no comments).

**Web**, rated official, community-tested or guide-seller:
- Blizzard Watch on Forever joining the maintenance schedule ([blizzardwatch.com, 2026-11-03](https://blizzardwatch.com/2026/11/03/speedy-warcraft-maintenance-day-now-added-wow-forever-maintenance/)). Community news. Launch on Wednesday 11-04; Tuesday maintenance was a pre-launch prediction. Seen only as a search snippet.
- Blizzard's Forever hotfixes, 2026-11-10 ([forum](https://us.forums.blizzard.com/en/wow/t/2403040/6)). Official. Plus news coverage ([Icy Veins](https://www.icy-veins.com/wow-forever/news/class-changes-profession-improvements-ah-deposit-gold-buffs-wow-forever-hotfixes-november-10th/), [Warcraft Tavern](https://www.warcrafttavern.com/forever/news/class-economy-changes-wow-forever-hotfixes-for-november-10/)), which says the 1-copper deposit came with realm restarts and that 60-minute mail delivery is intended. This conflicts with PLANNING's later note that the change was pulled and is due 11-17; hence N2.
- TSM sale-rate thresholds of about 0.1–0.3. Community-tested: a third-party addon ([CurseForge PBS Sales Rate](https://www.curseforge.com/wow/addons/pbs-sales-rate-tsm-regionsalerateavg)) and r/woweconomy threads, seen as search snippets. Not official TSM guidance.
- [Engadget 2012, "What days should you buy or sell"](https://www.engadget.com/2012/02/07/what-days-should-you-buy-or-sell-on-the-auction-house/). Community and old retail: supply falls after the Tuesday reset and restocks at weekends. Not tested on Forever.
- Forever gold guides ([IGGM](https://www.iggm.com/news/wow-forever-afk-gold-making-best-crafting-methods-for-casual-players), [Odealo](https://odealo.com/articles/best-gold-making-methods-world-of-warcraft-forever-guide)). Guide-seller. Little Forever-specific market data.

**Couldn't fetch** (these hosts would need to be allowed in the session's network settings):
- `warcraft.wiki.gg` (a community auction house guide on cornering and reset risks)
- `saddlebagexchange.com` (a community market-overview tool, relevant to #11)
- `tradeskillmaster.helpjuice.com` (TSM's sniper documentation)

**From memory, unverified:**
- Crystal Vial being sold by vendors.
- Arcanite transmute having a cooldown.
- The names of the game tables for cooldowns, bind status and quest use.

All are flagged where used.
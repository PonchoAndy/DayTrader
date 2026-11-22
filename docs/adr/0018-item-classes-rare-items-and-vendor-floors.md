# 0018. How analysis groups items: ammunition on its own, rare items as a separate class, vendor price as a floor marker

- **Status:** Accepted
- **Date:** 2026-11-22
- **Issue:** PonchoAndy/DayTrader#118, #120, #121

## Context

The Analyst's first full-market report (2026-11-22) raised three questions about how items are grouped and
read:
- Ammunition is ~half of all units sold but 0.3% of the gold. It filled 14 of the top 15 places by units
  (#118).
- Expensive one-of-a-kind gear (Skullflame Shield, Plans: Lionheart Helm, …) is often a single listing. Its
  sales are noisy, because a cancel-and-repost looks like a sale (#120).
- About 6–8% of units with a vendor price sell where the seller nets less than vendoring. The Analyst
  offered a weekly "better to vendor" list (#121).

## Decision

- **Ammunition gets its own table** in volume rankings (#118). The owner thinks of ammo in **stacks of 200**,
  so its tables show stacks as well as units. The table also shows whether each ammo type is vendor-sold,
  player-made or both.
- **Rare and expensive items are their own class**, "rare / collectible" (#120). It's read the way rare art
  sells: few sales, wide price ranges, judged one sale at a time rather than by volume.
  - It covers expensive one-off gear, rare plans and recipes, and **Bind on Equip epics**.
  - It's watched as a possible source of large value, but treated as **speculative**.
  - It's kept out of the volume and gold rankings for ordinary goods, so its noise doesn't distort them.
- **Buying from the AH to sell to a vendor is never a strategy**, only a last resort (#121). There's no
  "better to vendor" list. Instead, **an item trading near its vendor price is a floor marker**: the downside
  is limited, and there may be room to move up. Analysis uses it as a signal.

## Consequences

- The Analyst needs a working definition of "rare / collectible": for example, epic quality, or
  Bind-on-Equip items with few sales a day and a high price per unit. It will propose one; Rule-of-thumb
  thresholds go in `.claude/agents/analyst.md` once tested.
- Rankings and pages (the Market Pulse page, the Ticker) show three groups: ordinary goods, ammunition and
  rare / collectible.
- The "sellers net less than vendoring" figure stays a market observation (hypothesis H-A5), not a list
  for the owner.

## Alternatives considered

- **#120:** keep rare items in the rankings marked "noisy" (the Analyst's default); drop items under 5 sales
  a day; count only certain sales. The owner chose a separate class, because these items behave like a
  different market.
- **#121:** a weekly list in the Analyst's report, or a Ticker tab. The owner doesn't plan to sell to vendors.

# DayTrader Prototype

A claude.ai artifact (https://claude.ai/artifact/6wreTZDzn3UnHySAhPz4Td) for exploring the app's user
experience before building it. It started as the "Auction Data Tour" (v1); v2 is the prototype.

- Pick ruleset, faction and auction house at the top; every panel follows: at a glance, supply floods
  (buy signals), shortages (sell signals), trades with Blackwater (after an assumed 5% / 15% AH cut),
  gaps with your faction's other houses, and an in-game check to learn what a "house" is.
- Every item is identified by name + version ("Archer's Cloak of the Eagle"); versions are separate
  products, never merged or compared.
- `template.html` is the page with a `__UXDATA__` placeholder; `data-tour.html` is the published page
  with data embedded. The data comes from four local snapshots (2026-11-13 23:17 to 2026-11-14 03:17 UTC).
  Ruleset doesn't change the numbers: every ruleset currently returns the same houses.
- Filters: floods/shortages compare 23:17 with 03:17 for products worth >= 10 g listed, with >= 10 units
  at the relevant end and price moves capped at 300%. Trades need >= 20% and >= 0.20 g profit per unit
  and >= 3 listings in the selling market.

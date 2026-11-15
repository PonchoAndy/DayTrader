# 0011. Money is whole copper underneath; shown as gold with four decimals

- **Status:** Proposed (Architect, 2026-11-15, from the owner's suggestion; waiting for the owner's OK on #61)
- **Date:** 2026-11-15
- **Issue:** PonchoAndy/DayTrader#61

## Context

WoW money is gold/silver/copper: 1 g = 100 s = 10,000 c. Blizzard's API gives every price in whole
copper: commodities as `unit_price` per unit, auctions as `buyout` for the whole listing (`bid` on
~0.2%, dropped). Everything we store is already whole copper: hourly summaries (int64), listing flows
(int64), the market export (integers, null = not listed), vendor prices (Blizzard integers).
Prices seen run from 1–3c (Mild Spices) through 15c (Malachite), ~1s (Copper Ore) and 15–31s
(Thorium Bar) to gear around 1 g and absurd listings near Blizzard's cap (about 10M gold in retail,
unverified for Forever).

Fractions of a copper appear only in derived values: auction buyout ÷ quantity (we floor it today),
medians of an even count, per-unit fees (5% of a 3c item), vendor buy price per unit. Floating-point
gold can't hold most copper amounts exactly (0.0015), so sums drift and equality tests fail. The run
report's 2-decimal gold shows a 3c item as "0.00g". The owner proposed gold with 4 decimals
(1g 1s 1c = 1.0101), which is copper with the decimal point moved: lossless, sortable and aligned.
The Designer's mock-ups use coin units per comparison (#61 option b).

## Decision

**Data (Architect):**
- Money is stored and passed around as integer copper (int64 in Parquet, plain integers in JSON).
  Missing is null, never 0; a vendor price of 0 is a real value.
- Calculations stay in copper. Values that can be fractional stay float copper (never float gold)
  until the end, and are rounded once, half away from zero, when stored as an integer or displayed.
- Formatting happens only at the last step, with integer arithmetic, through one shared helper (Python
  and a JS twin). Sorting always uses the integer.
- Advisor agents receive integer copper, the unit stated once (`money_unit: "copper"`), and a `fmt`
  string per money field to quote. Ratios ("× vendor") are computed from integers and shown to 2
  significant figures, "—" when the vendor price is 0 or unknown.
- Auction per-unit prices keep `buyout // quantity` until the share of stacked auctions is measured.

**Display (Designer owns the look):**
- Money is shown as gold with 4 decimals everywhere it's compared: 1.0101, 0.0600, 0.0015. One format
  across pages, reports and advisor text. Right-aligned, fixed-width digits.
- The copper pair must be visually distinct, so 0.06 (6 s) and 0.0006 (6 c) can't be confused.
- Per-unit amounts under 1 copper are shown per trade, never as 0.0000 (a non-zero value that rounds to
  0 shows "< 0.0001").
- Prose and headlines may round amounts of 100 g or more to whole gold. Tables keep 4 decimals.

## Consequences

- Nothing stored needs converting; no storage cost.
- One formatter replaces `report.py`'s 2-decimal `gold()`; the pages and advisors use its twin.
- Changing the look later (coins, "1g 01s 01c") touches only the formatter, never data.
- Follow-ups: flows' "missing" prices become null (today `fillna(0)` makes `cur_min_price` / `wall_price` 0);
  `depth_gold_*` documented as copper; the report's unit-price cap comment corrected (the code caps at
  100,000 g, not 10M g); measure stacked auctions.
- Vendor prices (#70) follow the same contract: integer copper, null = unknown.
- The Stockpile Ledger prototype (`tools/stockpile-ledger/`) already follows it.

## Alternatives considered

- **Float gold in storage:** inexact for most copper amounts; rejected.
- **Coins, one unit per comparison (#61 b):** reads like the game, but the same item appears in
  different units in different views, and it needs a rule per view. Kept as the fallback look.
- **Full coin text "1g 01s 01c":** unambiguous but wide, and columns don't line up for scanning.
- **Exact (fractional) per-unit auction prices in the hourly summaries:** changes a column's type
  mid-series for an effect under 1c a unit; wait for the measurement.

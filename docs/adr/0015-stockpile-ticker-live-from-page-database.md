# 0015. Stockpile Ticker updates itself: numbers hourly, Analyst briefings every 6 hours

- **Status:** Accepted
- **Date:** 2026-11-20
- **Issue:** PonchoAndy/DayTrader#99

## Context

The Stockpile Ticker page had its numbers and the Economist's notes written into the page, so it changed only
when a Claude session republished it. The owner wants it current every hour, with the Analyst's read of each
holding. GitHub Actions can't publish a claude.ai page; only Claude can write to it. Claude sessions can't read
R2, so they need an export on GitHub. Actions minutes are already ~1,250 of 2,000 a month.

Options put to the owner (chat, 2026-11-20): (a) numbers and briefings hourly, (b) numbers hourly and briefings
every 6 hours plus on big moves, (c) briefings once a day. The owner chose **(b)**.

## Decision

- **GitHub, hourly:** a step at the end of the collect job (`collector/ticker.py`) appends the newest hour for
  the held items on house 114 to `tools/stockpile-ticker/ticker.json` on the data-only branch `analyst-data`.
  It runs in the same job so a run stays within the one-minute billing unit, and it can't fail the collection.
  Holdings come from `tools/stockpile-ticker/positions.json` (copied from the Stockpile Ledger).
- **Page:** reads its numbers (`ticker/data`), the Analyst's briefings (`briefings/*`) and the Economist's
  stance (`verdicts/economist`) from its own artifact database, live. Valuations are computed in the page.
- **Claude, hourly at :15:** a scheduled task ("Stockpile Ticker hourly update", prompt in
  `tools/stockpile-ticker/HOURLY.md`) copies the numbers in. `tools/stockpile-ticker/update.py` decides when a
  briefing is due: at each 6-hour mark (00, 06, 12, 18 UTC; at least 3 hours after the last one) or when a held
  item's lowest price moves 30% or more since the last briefing. Then the Analyst agent writes it.
- The Economist's stance stays separate and changes only at an Economist review.

## Consequences

- About 24 short Claude runs a day, ~4–6 of them with an Analyst briefing, come out of the owner's Claude usage.
- The page shows "Delayed" when the newest hour is over 3 hours old; GitHub skips ~3 hours a day (#28).
- Changing holdings means editing `positions.json` on `main` (the ticker re-reads every hour from 11-14).
- "Units sold" now comes from listing flows' clean estimate, so day totals differ a little from the first
  version of the page (which used the market export).
- A 30% threshold is a first guess: hourly prices swing a median ~23% over 12 hours. Revisit after a week.

## Alternatives considered

- **Hourly briefings (a):** ~6× the Claude usage for notes that would mostly say "no change".
- **A separate hourly Actions job:** ~720 extra minutes a month, over the 2,000-minute allowance.
- **Republishing the page each hour:** works, but every run rewrites the whole page; the database keeps runs small.
- **Page fetching data from GitHub itself:** the page can't reach GitHub (the viewer blocks outside requests).

# 0020. The addon scans the auction house only within the game's own limits

- **Status:** Proposed
- **Date:** 2026-11-25
- **Issue:** PonchoAndy/DayTrader#134, #136 (full scans, decided 2026-11-23), #138 (only the owner, decided 2026-11-23)

## Context

The owner wants an in-game addon that takes full auction-house scans while they stand at the AH, "as often as it can
within TOS" (#136). Forever uses retail's auction toolkit. A full scan (`C_AuctionHouse.ReplicateItems`) is allowed
once per 15 minutes per account in retail; Forever's limit is unmeasured. Full scans once disconnected players on houses
over 80,000 listings (fixed in retail patch 9.0.2); house 114 has ~180,000. Addons can't use the internet, so data leaves
the game only through the SavedVariables file. Blizzard's addon policy requires addons to be free and open-code and to
harm no realm or player. ADR 0013 already says the addon stays read-only and advisory. Plan:
`docs/designs/2026-11-25-addon-scan-plan.md`.

## Decision

The addon follows these rules:

1. It scans only while the AH window is open, and stops when it closes.
2. It runs at most one full scan per throttle window: **16 minutes** from the last successful scan, counted across the
   account and saved in the file. It never tries faster than the game allows. It may follow a shorter limit only if
   Forever is measured to allow one and the owner agrees.
3. When the game isn't ready or refuses, it asks once more on the game's "ready" signal, then waits a whole window. No
   retry loops. Each refusal is logged.
4. The player's own searches, buys and posts come first; a timed scan waits until they've been quiet for ~10 seconds.
5. It sends no automatic queries other than the full scan. It may record the search results the player opens by hand.
6. It reads results in pieces (~2,000 listings per frame).
7. It never posts, buys, bids or cancels, sends no key presses, doesn't read game memory, and doesn't stop the game
   logging an idle character out.
8. If a scan seems to have ended in a disconnect, automatic scanning turns off until the owner turns it back on.
9. It keeps no other players' names (pending #137).
10. It's for the owner only (#138). If it's ever shared, it's free with its code visible.

## Consequences

- At best one market snapshot every ~16 minutes, and only while the owner is at the AH. The hourly API pulls stay
  the main source (ADR 0002). Addon scans add finer snapshots and the owner's own trades.
- Full scans have no auction IDs, so they can't feed listing flows. Sales stay hourly.
- Follow-up: the test addon measures Forever's real limit, scan time, file size, and whether a scan needs a click.
  Delivery of the file is #135.

## Alternatives considered

- **Scan on a fixed timer, ignoring the game's ready signal:** risks refused queries piling up, and looks like the
  flooding the throttle exists to stop.
- **Item-by-item searches between full scans** (a watchlist refreshed every minute): more server load for data the
  next full scan brings anyway. It could come later, under its own rules, if a real need appears.
- **No full scan, own trades only** (the Researcher's first suggestion on #136): turned down by the owner, who wants
  scans like Auctionator's.

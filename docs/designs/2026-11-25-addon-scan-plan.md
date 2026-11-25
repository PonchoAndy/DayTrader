# Plan: the DayTrader addon, from the auction house to our data

- **Date:** 2026-11-25 · **Status:** draft for the owner. Proposed ADR 0020 holds the rules.
- **Issues:** PonchoAndy/DayTrader#134 (research), #136 (decided: full scans as often as the game allows), #138
  (decided: only the owner installs it), #135 and #137 (still open) · **Phase:** 3, "AH terminal" (ADR 0013), started
  early at the owner's request

## What we want

While the owner stands at an auction house with the window open, a small addon takes a **full scan** of every listing
as often as the game allows. It saves the scans, plus the owner's own trades, to the file the game writes on logout.
That file then comes into our storage (R2), next to the hourly API pulls. The Ticker and the agents can then read
market snapshots every ~15 minutes while the owner is playing, instead of one an hour.

```
In game                            Owner's computer               Our storage and pages
-------                            ----------------               ---------------------
DayTrader addon                    SavedVariables file            R2: addon/us/114/...
  scans while the AH is open  ──►  DayTrader.lua           ──►    importer (Python)
  records own trades               (written on /reload,           Ticker, agents
  never buys, posts or cancels      logout or quit)
                                   delivery: #135 (open)
```

## What the game gives us (from #134; checked again 2026-11-25)

- **The full scan is `C_AuctionHouse.ReplicateItems()`.** The game sends every listing to the client, and the addon
  reads them one by one (`GetReplicateItemInfo`).
- **The throttle is one successful full scan per 15 minutes, per account** [warcraft.wiki.gg, retail]. Forever uses the
  same toolkit; its own limit hasn't been measured yet.
- **Each listing gives** item ID, quantity, buyout, minimum bid and time left. It gives **no auction ID**, and since
  patch 9.0.2 **no seller name** (only your own listings show yours). Name and item link arrive a moment later, as the
  game loads each item.
- **Large houses were a problem once.** Before 9.0.2, full scans disconnected players on houses with more than 80,000
  listings. That was traced to seller names and fixed by dropping them. House 114 has ~180,000 listings, so the first
  test should be watched closely.
- **The game delivers at most ~2,000 listings per frame**, so a scan on 114 takes many frames to arrive (seconds, not
  a freeze, if we read it in small pieces).
- **Not known yet:** whether a full scan has to start from a click or key press, or can start from a timer. The wiki
  doesn't say. The first test settles it (step 1 below).

## The polite scanning rules (proposed ADR 0020)

These are the rules that keep us inside Blizzard's terms. The addon follows all of them, always:

1. **Only while the AH window is open.** Scanning starts when the window opens and stops the moment it closes. Walking
   away, mounting or a loading screen closes it.
2. **One full scan per window, never faster than the game allows.** The addon waits **16 minutes** (the 15-minute limit
   plus a minute of margin) from the last successful scan, counted across all the owner's characters, because the limit
   is per account. The time is saved in the file, so a relog or `/reload` doesn't reset it.
3. **Ask once, then wait.** If the game says it isn't ready (`IsThrottledMessageSystemReady` is false) or refuses the
   scan, the addon doesn't retry in a loop. It waits for the game's "ready" signal, then tries once more; after a second
   refusal it waits a whole window. Every refusal is logged with its time, which is how we measure Forever's real limit.
4. **The player goes first.** If the owner is searching, buying or posting, the timed scan waits until they've been quiet
   for about 10 seconds. Their own actions use the same budget, and theirs matter more.
5. **No other automatic queries.** No looped searches, no item-by-item polling. The addon also records the search
   results the owner opens by hand. That costs the server nothing extra.
6. **Read gently.** The addon reads the arriving listings in pieces of ~2,000 per frame, so the game stays smooth.
7. **Read-only, always.** The addon never posts, buys, bids or cancels. It has no "buy" button, and the game would block
   one anyway. It sends no key presses and doesn't read the game's memory, and it doesn't keep the character from going
   idle. If the game logs an idle character out (after about 30 minutes), that's the end of the session.
8. **A safety stop.** The addon marks "scan in progress" in the file. If it finds that mark still set at the next login,
   the last scan probably ended in a disconnect, so automatic scanning turns off until the owner switches it back on.
   `/dt pause` stops it at any time.
9. **The "Scan now" button follows the same rules.** It's greyed out with a countdown until the window has passed.

Why this is inside the rules: Blizzard's addon policy allows free, open-code addons that don't harm realms or players.
The throttle *is* the game's own limit on how often an addon may scan. Auctionator does the same full scan when you
open the AH. And the companion step (reading the saved file after the game writes it) is how TSM's desktop app and
similar uploaders work. What would break the rules: getting around the throttle, automating trades, anti-idle tricks,
or software that reads or drives the game client.

## What the addon saves

- **Each time the AH opens:** time (UTC and game time), the hidden realm number from `UnitGUID("player")` (6929 for the
  owner's character, #133), faction, zone, and which auctioneer.
- **Each full scan:** start and end time, number of listings, how long it took, and the listings **grouped** by item,
  variant (the item link, for gear with random bonuses like "of the Bear"), unit price and time left, with total
  quantity and number of listings in each group. Grouping keeps the file small: the game reads the whole file at every
  login, and 180,000 single listings would make it tens of megabytes per scan.
- **The owner's own trades:** own listings (with time left), posts, purchases, and AH mail invoices (sale price,
  deposit, the exact cut). No other players' names (#137, default; the full scan has none anyway).
- **Housekeeping:** every refusal and its time, the client version, the addon version.
- **Size limit:** the file keeps the newest scans up to a set size (to be measured; start with about 4 hours' worth)
  and drops the oldest. The importer skips scans it already has, so nothing is lost as long as the file is delivered
  within that time.

## Getting the file to us (#135, open)

The game writes the file on `/reload`, logout or quit, never while you play. It's probably at
`World of Warcraft\_forever_\WTF\Account\<ACCOUNT>\SavedVariables\DayTrader.lua`. The options are on #135:

- **(a) Drop the file into a Claude chat after playing.** No install. Fine for the first tests, but it gets tedious, and
  scan files may be large.
- **(b) A small uploader on your computer**, run when you finish playing. It reads the file and sends it to R2 with a
  key that can only write new addon files. One install, then nothing to do.
- **(c) A Claude Code session on your computer** (Remote Control) picks the file up when asked.

**Suggestion:** (a) for the first one or two test sessions, while the file format settles, then (b).

## How the data joins the rest

- An **importer** (`collector/addon_import.py`) reads the Lua file and writes one parquet file per scan to
  `addon/<region>/<house>/scans/<YYYY-MM-DD>/<HHMMSS>.parquet`, in the same shape as our hourly listing summaries.
  Own trades go to `addon/<region>/trades/`.
- **Which house:** the realm number names the ruleset (6929 → Normal → house 114 for Horde). A check matches each
  scan's prices against the nearest hourly API pull, and flags a scan that doesn't fit.
- **The Ticker** gets in-between points: hourly bars stay as they are, addon scans show as dots where they exist.
- **What addon scans can't do:** they have no auction IDs, so they can't feed listing flows (sales). Sales stay hourly,
  from the API. Scans add finer price and quantity snapshots, and the owner's own trades add real fill rates (#129).

## Build steps

0. **Owner, 2 minutes in game.** Type these and tell Claude what they print:
   - `/run print(GetBuildInfo())` — the client version, so the addon's file declares the right one;
   - the folder that holds `Interface\AddOns` (look in the game's install folder for `_forever_`).
1. **Test addon** (`addon/DayTrader/` in this repo). One "Scan now" button and nothing automatic. It records identity,
   scan duration, listing count, file size, whether the scan worked from a button only (the click-or-timer question),
   and what happens on a second press inside 15 minutes. Owner: copy the folder into `Interface\AddOns`, open the AH,
   press the button once, wait, press again, `/reload`, and send the file.
2. **Timed scans** under the rules above, plus own-trade capture. A short in-game session to check.
3. **Importer and storage**, then addon dots on the Ticker.
4. **Uploader**, if #135 goes that way.

## Decisions needed from the owner

- **Accept the scanning rules** (proposed ADR 0020), or change any of them.
- **#135:** how the file reaches us (suggested: drop it in a chat for the tests, then an uploader).
- **#137:** other players' names (suggested: don't keep them).
- **Start automatically?** When the AH opens and the window has passed, scan at once (suggested), or only after a
  "start" click each visit.

## Sources

- [warcraft.wiki.gg: C_AuctionHouse.ReplicateItems](https://warcraft.wiki.gg/wiki/API:C_AuctionHouse.ReplicateItems)
  (throttle, 80k-listing disconnects, ~2,000 per frame, 9.0.2 change), read 2026-11-25. Retail; Forever untested.
- [warcraft.wiki.gg: GetReplicateItemInfo](https://warcraft.wiki.gg/wiki/API:C_AuctionHouse.GetReplicateItemInfo)
  (return values; no auction ID; owner nil), read 2026-11-25.
- [warcraft.wiki.gg: IsThrottledMessageSystemReady](https://warcraft.wiki.gg/wiki/API_C_AuctionHouse.IsThrottledMessageSystemReady),
  read 2026-11-25.
- PLANNING §1, "Path B confirmed for Forever" (Researcher, 2026-11-23): Forever's toolkit, saved-file path, addon
  policy.

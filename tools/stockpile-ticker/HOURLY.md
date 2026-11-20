# Stockpile Ticker: the hourly Claude run (#99)

A scheduled task, **"Stockpile Ticker hourly update"**, starts a fresh Claude session at :15 past every hour
and gives it the prompt below. Edit the prompt in the task (claude.ai → Code → Scheduled tasks) and keep this
copy in step. Page: https://claude.ai/artifact/CfWFQPhkPehTQkdktHtrHw

## Page database (ArtifactData, the page's URL)

| Doc | Written by | Holds |
|---|---|---|
| `ticker/data` | every hourly run with new data | numbers for the last 14 days (`update.py` → `data.json`) |
| `ticker/state` | every hourly run | `{lastHour, lastBriefingAt, pricesAtBriefing: {item id: copper}, lastRunAt}` |
| `briefings/<item id>` | runs with a briefing due | `{text, writtenAt, reasons}`: the Analyst's note on that holding's card |
| `briefings/overall` | runs with a briefing due | `{headline, watch: [status per Economist watch item], writtenAt, reasons}` |
| `verdicts/economist` | a Claude session after an Economist review | `{asOf, headline, nextReview, items: {id: {stance, why}}, watch: [...]}` |

## Prompt

```
Stockpile Ticker hourly update (PonchoAndy/DayTrader#99). Work quietly and briefly; this runs every hour.
Don't commit or push anything, don't open issues or PRs, and skip the Issue Deck start-of-session steps.

Page: https://claude.ai/artifact/CfWFQPhkPehTQkdktHtrHw (write with the ArtifactData tool; load it with ToolSearch).
W = your scratchpad directory.

1. In the DayTrader checkout (clone PonchoAndy/DayTrader if there is none): git fetch -q origin main analyst-data.
   If origin/main has no tools/stockpile-ticker/update.py, stop: the feature isn't merged yet.
   git show origin/main:tools/stockpile-ticker/update.py > W/update.py
   git show origin/analyst-data:tools/stockpile-ticker/ticker.json > W/ticker.json  (missing: stop, nothing to do)
2. ArtifactData get ticker/state with out_dir W/db (it may not exist yet: then there is no state file).
3. python3 W/update.py --ticker W/ticker.json --state W/db/ticker/state.json --out W/out
   It prints {newest_hour, new_data, briefing_due, reasons, prices}.
4. If new_data: ArtifactData get ticker/data (for its version), then set ticker/data from file W/out/data.json
   (if_version = that version; omit if the doc doesn't exist).
5. If briefing_due: read W/out/brief.json and the doc verdicts/economist (its watch list), then call the
   analyst agent (Agent tool, subagent_type "analyst") with brief.json's contents, the watch list, and this ask:
   "Write the Stockpile Ticker briefing. For each held item, 2-4 plain sentences for the owner: what the lowest
   and middle price, units listed and sales did since the last briefing and over the last 24-48 hours, and
   whether that is normal for this item and hour (label observation / pattern). Prices as gold with 4 decimals
   (copper / 10000), times in US Eastern on the 24-hour clock with UTC in brackets, e.g. 14:25 ET (19:25 UTC). No trade calls. Also a one-sentence headline for
   the whole stockpile, and for each Economist watch item, in order, a short status (e.g. 'Not yet: 3 of the
   last 24 hours at 0.0300+'; no numbering). Reply with JSON only: {headline, watch: [..], items: {<item id>: text}}."
   Spot-check any hour counts and prices it quotes against brief.json and fix mistakes before writing.
   Then one ArtifactData batch: set briefings/<id> {text, writtenAt: now ISO, reasons} for each item,
   set briefings/overall {headline, watch, writtenAt, reasons}. Read the existing docs first for if_version.
6. Set ticker/state to {lastHour: newest_hour, lastRunAt: now ISO, lastBriefingAt and pricesAtBriefing:
   now and `prices` if you wrote a briefing, else unchanged from the old state} (if_version from step 2).
7. Reply with one line: newest hour, whether numbers and briefings were written, and why.
If anything fails, say what failed in one line and stop; the next hour tries again.
```

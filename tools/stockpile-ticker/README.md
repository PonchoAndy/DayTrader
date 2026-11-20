# Stockpile Ticker

Private claude.ai page charting the owner's stockpile positions like a stock ticker:
https://claude.ai/artifact/CfWFQPhkPehTQkdktHtrHw. Live since 2026-11-20 (#99, ADR 0015).

- `stockpile-ticker.html`: the page. It holds no data: it reads its artifact database (docs listed in
  `HOURLY.md`). Republish to the same URL with the Artifact tool's `url` only when the page's code changes.
- `positions.json`: what the owner holds (from the Stockpile Ledger). Edit on `main` when the ledger changes.
- `collector/ticker.py`: runs at the end of every hourly collect job and commits `ticker.json` to branch
  `analyst-data`. The workflow's **ticker** switch runs only this step.
- `update.py`: used by the hourly Claude task. Trims the export to 14 days for the page and says when an
  Analyst briefing is due (6-hour marks, or a 30% move).
- `HOURLY.md`: the scheduled task's prompt and the page's database layout.

After an Economist review, update the doc `verdicts/economist` (stance, why, watch list, next review).

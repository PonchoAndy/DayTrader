# Overnight Market demo

A claude.ai artifact replaying the stored hourly data: the supply "tide" per faction, an item explorer
(price and units listed per house, hour by hour), and the items whose supply drained most.

To refresh it with newer data:
1. GitHub → Actions → Collect auctions → Run workflow, pick this branch, tick **demo**. The run writes
   `demo-data.json` (from `collector/report.py --demo`) and commits it to the branch.
2. `python tools/overnight-demo/build.py` embeds it into `overnight-demo.html`, which is what's published.

Items are picked automatically (≥ 5 silver on Horde house 113, listed nearly every hour): biggest
supply drains ("bought up"), biggest price swings, biggest markets by value, and biggest Horde vs
Alliance price gaps.

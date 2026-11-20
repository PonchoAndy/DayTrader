# Analyst data (#19)

- `watchlist.json`: the items (and houses per region) the daily export follows hour by hour. Edit it
  on `main` to add or drop items; the next daily run rebuilds the whole file for the new list.
- `pulse.json`: the export itself (`collector/pulse.py`). It is **not on `main`**: the daily run
  (12:00 UTC, lands ~12:30–13:05) commits it to the data-only branch `analyst-data`. Read it with

  ```bash
  git fetch --depth 1 origin analyst-data && git show FETCH_HEAD:tools/analyst/pulse.json > /tmp/pulse.json
  ```

  then, e.g. in Python:

  ```python
  import json, pandas as pd
  d = json.load(open("/tmp/pulse.json")); us = d["regions"]["us"]
  t = pd.DataFrame(us["items"]["114"]["249391"], index=pd.to_datetime(us["hours"]))   # Pyrite on 114
  tot = pd.DataFrame(us["totals"]["114"], index=pd.to_datetime(us["hours"]))         # whole market, 114
  ```

Fields, units and caveats: `notes` in the file and "Every hour for the Analyst" in `collector/README.md`.
In short: UTC times, copper, null = unknown (never zero), and the newest ~12 hours have no flows yet
(flows are built nightly at ~01:35 UTC).

Rebuild by hand: Actions → Collect auctions → Run workflow → branch `main` → tick **pulse** → Run.

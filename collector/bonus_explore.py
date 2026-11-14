"""One-off exploration for #30: which source names our bonus IDs ("of the Monkey"…)?

Runs on GitHub Actions (Claude's cloud environment can't reach these sites).
Usage: python collector/bonus_explore.py 12718,12719,...
"""

import csv
import io
import json
import sys

import requests

IDS = {int(x) for x in sys.argv[1].split(",")} if len(sys.argv) > 1 else set(range(12718, 12761))
UA = {"User-Agent": "DayTrader-collector/0.1 (personal project)"}


def fetch(url):
    try:
        r = requests.get(url, headers=UA, timeout=60)
        print(f"\n=== {url} -> HTTP {r.status_code}, {len(r.content)} bytes")
        return r if r.ok else None
    except requests.RequestException as e:
        print(f"\n=== {url} -> {type(e).__name__}: {e}")
        return None


# 1. Raidbots: how high do its bonus IDs go?
r = fetch("https://www.raidbots.com/static/data/live/bonuses.json")
if r:
    keys = sorted(int(k) for k in r.json() if k.isdigit())
    print("raidbots bonus id range:", keys[0], "-", keys[-1], "· ours present:", sorted(IDS & set(keys))[:10])

# 2. wago.tools: which game products/branches does it track?
r = fetch("https://wago.tools/api/builds")
branches = []
if r:
    data = r.json()
    branches = list(data.keys()) if isinstance(data, dict) else []
    print("products:", branches)
    for b in branches:
        if any(w in b.lower() for w in ("forever", "plunder", "event", "labs", "ptr", "beta")):
            latest = data[b][0] if isinstance(data[b], list) and data[b] else data[b]
            print("  ", b, json.dumps(latest)[:200])

# 3. Try ItemBonus on every branch that isn't plain retail/classic; report whether our IDs appear.
for b in branches:
    r = fetch(f"https://wago.tools/db2/ItemBonus/csv?branch={b}")
    if not r:
        continue
    rows = list(csv.DictReader(io.StringIO(r.text)))
    hits = [x for x in rows if x.get("ParentItemBonusListID", "").isdigit() and int(x["ParentItemBonusListID"]) in IDS]
    mx = max((int(x["ParentItemBonusListID"]) for x in rows if x.get("ParentItemBonusListID", "").isdigit()), default=None)
    print(f"branch {b}: {len(rows)} rows, max ParentItemBonusListID {mx}, rows for our IDs: {len(hits)}")
    for x in hits[:12]:
        print("   ", dict(x))

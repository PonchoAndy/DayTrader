"""One-off exploration for #30: which community source names our bonus IDs ("of the Monkey"…)?

Runs on GitHub Actions (Claude's cloud environment can't reach these sites). Prints, for each
source, its format and the rows matching the given bonus IDs. Read the output in the job log.
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
        print(f"\n=== {url} -> HTTP {r.status_code}, {len(r.content)} bytes, {r.headers.get('content-type')}")
        return r if r.ok else None
    except requests.RequestException as e:
        print(f"\n=== {url} -> {type(e).__name__}: {e}")
        return None


r = fetch("https://www.raidbots.com/static/data/live/bonuses.json")
if r:
    data = r.json()
    items = data.items() if isinstance(data, dict) else ((str(x.get("id")), x) for x in data)
    items = list(items)
    print("entries:", len(items), "sample:", json.dumps(items[0])[:400])
    for k, v in items:
        if k.isdigit() and int(k) in IDS:
            print(k, json.dumps(v)[:300])

for branch in ("", "?branch=wow_classic", "?branch=wow_classic_era", "?branch=wow_anniversary"):
    for table in ("ItemBonus", "ItemNameDescription"):
        r = fetch(f"https://wago.tools/db2/{table}/csv{branch}")
        if not r:
            continue
        rows = list(csv.DictReader(io.StringIO(r.text)))
        print("columns:", list(rows[0].keys()) if rows else None, "rows:", len(rows))
        if table == "ItemBonus":
            hits = [x for x in rows if x.get("ParentItemBonusListID", "").isdigit() and int(x["ParentItemBonusListID"]) in IDS]
            print("rows whose ParentItemBonusListID is one of ours:", len(hits))
            for x in hits[:60]:
                print(dict(x))
        else:
            print("sample:", rows[:3])

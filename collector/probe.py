"""WoW Forever auction house probe (PonchoAndy/DayTrader#9).

Pulls one full snapshot of every auction house in a region and reports what came back:
auctions per house, response sizes, distinct items, refresh timestamps, and how many item
IDs the item endpoint can't resolve.

Raw responses are saved gzipped under data/raw/<timestamp>/ (data/ is git-ignored), and a
summary is written to data/raw/<timestamp>/summary.json.

Credentials:
- In GitHub Actions or locally, set BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET.
- In Claude's cloud sessions, leave them unset: the network proxy adds the key for
  oauth.battle.net automatically.

Usage: python collector/probe.py [--region us] [--ruleset 2] [--item-sample 200]
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent


def get_token(session: requests.Session) -> str:
    cid, secret = os.environ.get("BLIZZARD_CLIENT_ID"), os.environ.get("BLIZZARD_CLIENT_SECRET")
    auth = (cid, secret) if cid and secret else None  # None: the cloud proxy injects the key
    r = session.post("https://oauth.battle.net/token", data={"grant_type": "client_credentials"}, auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


class Api:
    def __init__(self, region: str):
        self.s = requests.Session()
        self.base = f"https://{region}.api.blizzard.com"
        self.dynamic = f"dynamic-forever-{region}"
        self.static = f"static-forever-{region}"
        self.s.headers["Authorization"] = f"Bearer {get_token(self.s)}"

    def get(self, path: str, namespace: str, retries: int = 3) -> requests.Response:
        url = self.base + path
        for attempt in range(retries):
            r = self.s.get(url, params={"locale": "en_US"}, headers={"Battlenet-Namespace": namespace}, timeout=120)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            return r
        return r


def faction_of(name: str) -> str:
    for f in ("Alliance", "Horde", "Blackwater"):
        if f.lower() in name.lower():
            return f
    return "Unknown"


def save(path: Path, raw: bytes) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as f:
        f.write(raw)
    return path.stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--region", default="us")
    ap.add_argument("--ruleset", type=int, default=2, help="2 = Normal")
    ap.add_argument("--item-sample", type=int, default=200, help="item IDs to look up for the 404 check")
    args = ap.parse_args()

    started = datetime.now(timezone.utc)
    outdir = ROOT / "data" / "raw" / started.strftime("%Y%m%dT%H%MZ")
    api = Api(args.region)

    rulesets = api.get("/data/wow/ruleset/index", api.dynamic).json()
    houses_r = api.get(f"/data/wow/ruleset/{args.ruleset}/auctions/", api.dynamic)  # trailing slash required
    houses_r.raise_for_status()
    houses = houses_r.json().get("auctions", [])
    print(f"Rulesets: {[r.get('id') for r in rulesets.get('rulesets', [])]}  ·  houses in ruleset {args.ruleset}: {len(houses)}")

    summary = {"started": started.isoformat(), "region": args.region, "ruleset": args.ruleset,
               "rulesets": rulesets.get("rulesets"), "houses": []}
    all_items: Counter[int] = Counter()
    t0 = time.time()

    for h in sorted(houses, key=lambda x: x["id"]):
        hid, name = h["id"], h.get("name", "")
        row = {"id": hid, "name": name, "faction": faction_of(name)}
        for kind, suffix in (("auctions", ""), ("commodities", "/commodities")):
            t = time.time()
            r = api.get(f"/data/wow/ruleset/{args.ruleset}/auctions/{hid}{suffix}", api.dynamic)
            info = {"status": r.status_code, "bytes": len(r.content), "seconds": round(time.time() - t, 1),
                    "last_modified": r.headers.get("last-modified")}
            if r.ok:
                body = r.json()
                listings = body.get("auctions") or []  # field is missing entirely on empty houses
                items = Counter(a["item"]["id"] for a in listings if "item" in a)
                all_items.update(items.keys())
                info.update(listings=len(listings), distinct_items=len(items),
                            quantity=sum(a.get("quantity", 1) for a in listings),
                            gz_bytes=save(outdir / f"house-{hid}-{kind}.json.gz", r.content))
            row[kind] = info
        summary["houses"].append(row)
        a, c = row["auctions"], row["commodities"]
        print(f"  {hid} {row['faction']:<10} auctions: {a.get('listings', a['status']):>6} ({a['bytes'] / 1e6:5.1f} MB)"
              f"  commodities: {c.get('listings', c['status']):>6} ({c['bytes'] / 1e6:5.1f} MB)"
              f"  updated {a.get('last_modified')}")

    summary["pull_seconds"] = round(time.time() - t0, 1)
    summary["total_bytes"] = sum(h[k]["bytes"] for h in summary["houses"] for k in ("auctions", "commodities"))
    summary["total_gz_bytes"] = sum(h[k].get("gz_bytes", 0) for h in summary["houses"] for k in ("auctions", "commodities"))
    summary["distinct_items_all_houses"] = len(all_items)

    # How many item IDs can the static item endpoint resolve? (community report: ~43% 404 on one EU house)
    sample = random.Random(0).sample(sorted(all_items), min(args.item_sample, len(all_items)))
    statuses: Counter[int] = Counter()
    names = {}
    for iid in sample:
        r = api.get(f"/data/wow/item/{iid}", api.static)
        statuses[r.status_code] += 1
        if r.ok:
            names[iid] = r.json().get("name")
    summary["item_lookup"] = {"sampled": len(sample), "status_counts": dict(statuses),
                              "found_pct": round(100 * statuses[200] / max(1, len(sample)), 1),
                              "example_names": dict(list(names.items())[:15])}

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nPulled {len(houses)} houses in {summary['pull_seconds']}s: {summary['total_bytes'] / 1e6:.1f} MB raw, "
          f"{summary['total_gz_bytes'] / 1e6:.1f} MB gzipped, {len(all_items)} distinct items.")
    print(f"Item lookup: {summary['item_lookup']['found_pct']}% of {len(sample)} sampled IDs found ({dict(statuses)}).")
    print(f"Saved to {outdir.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

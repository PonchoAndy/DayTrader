"""Hourly numbers for the Stockpile Ticker page (PonchoAndy/DayTrader#99), exported for Claude sessions
(which can't read R2). Run by the hourly collect job right after collecting, so it must stay quick: with
--prev it reads only hourly files it hasn't seen, and listing-flow days it hasn't seen (one new day a night).

Read-only on R2. Reads, for the region and house in tools/stockpile-ticker/positions.json:
  [<region>/]hourly/<date>/<snapshot>.parquet   the held items' lowest and middle price and units listed
  [<region>/]flows/<YYYY-MM>/<day>.parquet      units sold (clean, a low estimate) and posted per UTC day

Output (JSON; money in copper per unit; null = not listed or not known, never zero):
  {generated_at, since, region, house, positions: [...from positions.json],
   hours: ["YYYY-MM-DDTHH:MMZ", ...]            every stored snapshot, oldest first
   flow_hours: [h or null, ...]                 hours since the previous snapshot; null = flows not built yet
   items: {item_id: {min, median, qty, sold, posted, sale_max: [...]}}   one value per hour; sold (clean, a low
                                                estimate), posted and sale_max (highest unit price paid; null = no sale
                                                seen, or flows from before 2026-11-21) cover the hour(s) ENDING at
                                                that snapshot
   flow_days: ["YYYY-MM-DD", ...]               UTC days with listing flows built (nightly, ~01:35 UTC)
   flows: {item_id: {sold: [...], posted: [...]}}               one value per flow day}

Usage: python collector/ticker.py --out ticker.json [--prev old.json] [--local DIR] [--since 2026-11-14]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import LocalStore, R2Store, prefix  # noqa: E402
from flows import list_keys  # noqa: E402
from market import get_parquet  # noqa: E402
from pulse import load_flows  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COLS = ["house_id", "kind", "item_id", "variant", "quantity", "min_price", "median_price"]


def hour_of(key: str) -> str:
    """hourly/2026-11-19/20261119T0125Z.parquet -> 2026-11-19T01:25Z"""
    s = key.rsplit("/", 1)[1].split(".")[0]
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}T{s[9:11]}:{s[11:13]}Z"


def read_hour(store, key: str, house: int, ids: set[int]) -> dict:
    df = get_parquet(store, key, COLS)
    out = {}
    if df is None or not len(df):
        return out
    if "variant" not in df.columns:   # files before 2026-11-14 ~04:00 UTC merged variants
        df["variant"] = ""
    w = df[(df["house_id"] == house) & df["item_id"].isin(ids) & (df["variant"] == "")]
    w = w.sort_values("kind").drop_duplicates("item_id", keep="last")   # commodity row if sold both ways
    for r in w.itertuples():
        out[int(r.item_id)] = (int(r.min_price), int(r.median_price), int(r.quantity))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Export the Stockpile Ticker's hourly numbers (#99)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prev", help="the previous export: keep its hours and days, read only new files")
    ap.add_argument("--local", help="read this folder instead of R2")
    ap.add_argument("--positions", default=str(ROOT / "tools/stockpile-ticker/positions.json"))
    ap.add_argument("--since", default="2026-11-14", help="first UTC date to include")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()
    pos = json.loads(Path(args.positions).read_text())
    region, house = pos["region"], int(pos["house"])
    ids = {int(i["id"]) for i in pos["items"]}
    store = LocalStore(Path(args.local)) if args.local else R2Store(os.environ.get("R2_BUCKET", "daytrader-data"))

    prev = None
    if args.prev:
        try:
            prev = json.loads(Path(args.prev).read_text())
        except (OSError, ValueError) as e:
            print(f"No usable previous export ({type(e).__name__}); reading everything since {args.since}")
        if prev and (prev.get("since") != args.since or prev.get("house") != house or prev.get("region") != region
                     or set(prev.get("items", {})) != {str(i) for i in ids}):
            print("Previous export covers other items, house or dates; reading everything")
            prev = None

    # hourly prices: one file per snapshot, read only the new ones
    have = dict.fromkeys(prev["hours"]) if prev else {}
    rows = {h: {int(i): (prev["items"][i]["min"][n], prev["items"][i]["median"][n], prev["items"][i]["qty"][n])
                for i in prev["items"]} for n, h in enumerate(prev["hours"])} if prev else {}
    keys = [k for k in list_keys(store, f"{prefix(region)}hourly/")
            if k.endswith(".parquet") and k.rsplit("/", 2)[1] >= args.since and hour_of(k) not in have]
    with ThreadPoolExecutor(args.workers) as pool:
        for k, r in zip(keys, pool.map(lambda k: read_hour(store, k, house, ids), keys)):
            rows[hour_of(k)] = r
    hours = sorted(rows)
    if not hours:
        print(f"! no hourly files since {args.since}")
        return 1
    items = {str(i): {f: [(rows[h].get(i) or (None, None, None))[n] for h in hours]
                      for n, f in enumerate(("min", "median", "qty"))} for i in sorted(ids)}

    # listing flows: one file per UTC day, built nightly; read days not in the previous export.
    # Kept per hour (the hour ending at each snapshot) and summed per UTC day. An export from before hourly
    # sales were kept (#99) re-reads every flow day once.
    hourly_prev = bool(prev) and "flow_hours" in prev and all("sale_max" in v for v in prev["items"].values())
    days = list(prev["flow_days"]) if hourly_prev else []
    flows = {str(i): {f: list(prev["flows"][str(i)][f]) for f in ("sold", "posted")} if hourly_prev else {"sold": [], "posted": []}
             for i in sorted(ids)}
    # per-hour sales: {hour: hours_between} for hours with flows built, {(hour, item): (sold, posted)}
    fhours = {h: v for h, v in zip(prev["hours"], prev["flow_hours"]) if v is not None} if hourly_prev else {}
    fvals = {(h, int(i)): (prev["items"][i]["sold"][n], prev["items"][i]["posted"][n], prev["items"][i]["sale_max"][n])
             for i in prev["items"] for n, h in enumerate(prev["hours"]) if h in fhours} if hourly_prev else {}
    built = sorted(k.rsplit("/", 1)[1][:10] for k in list_keys(store, f"{prefix(region)}flows/") if k.endswith(".parquet"))
    new_days = [d for d in built if d >= args.since and d not in set(days)]
    if new_days:
        _, fw, fh = load_flows(store, region, new_days[0], {house}, ids)
        for ts, v in fh.items():
            if not pd.isna(v):
                fhours[pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%MZ")] = round(float(v), 2)
        if len(fw):
            snap = pd.to_datetime(fw["snapshot"], utc=True)
            fw["day"], fw["hour"] = snap.dt.strftime("%Y-%m-%d"), snap.dt.strftime("%Y-%m-%dT%H:%MZ")
            for r in fw.itertuples():
                fvals[(r.hour, int(r.item_id))] = (int(r.sold_clean), int(r.posted), int(r.sale_max) or None)
            per = fw.groupby(["day", "item_id"])[["sold_clean", "posted"]].sum()
        for d in new_days:
            days.append(d)
            for i in sorted(ids):
                got = len(fw) and (d, i) in per.index
                flows[str(i)]["sold"].append(int(per.loc[(d, i), "sold_clean"]) if got else 0)
                flows[str(i)]["posted"].append(int(per.loc[(d, i), "posted"]) if got else 0)

    # per hour: null = flows not built yet for that hour (never zero); built but no row for the item = 0
    flow_hours = [fhours.get(h) for h in hours]
    for i in sorted(ids):
        for n, f in enumerate(("sold", "posted", "sale_max")):
            items[str(i)][f] = [None if h not in fhours else (fvals.get((h, i)) or (0, 0, None))[n] for h in hours]

    if prev and hourly_prev and not keys and not new_days:   # nothing new (the collector skipped this hour): leave the file as is
        Path(args.out).write_text(Path(args.prev).read_text())
        print(f"Ticker export: nothing new since {prev['generated_at']}; newest {hours[-1]}")
        return 0
    res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "since": args.since,
           "region": region, "house": house, "bought_at": pos.get("bought_at"), "positions": pos["items"], "hours": hours, "flow_hours": flow_hours, "items": items,
           "flow_days": days, "flows": flows}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, separators=(",", ":")) + "\n")
    print(f"Ticker export: {len(hours)} hours ({len(keys)} new), {len(days)} flow days ({len(new_days)} new), "
          f"newest {hours[-1]} -> {args.out} ({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Hourly market pulse for the Analyst agent (PonchoAndy/DayTrader#19), exported for Claude sessions
(which can't read R2). Unlike market.py it never thins old hours: time-of-day and weekday patterns need
every hour.

Run daily by the workflow (12:00 UTC, after the trading day closes, ADR 0014; with --prev it re-reads only
the last few days) and by its "pulse" switch (a full rebuild).
Read-only on R2. Reads, per region (never mixed: house IDs repeat across regions, ADR 0009):
  [<region>/]hourly/<date>/*.parquet          every hourly summary since --since
  [<region>/]flows/<YYYY-MM>/<day>.parquet    hourly listing flows (#37), built nightly at ~01:35 UTC
and the watchlist (items, and houses per region) from tools/analyst/watchlist.json.

Output (JSON, compact; one array value per snapshot in `hours`; money in copper as integers):
  {generated_at, since, price_fields, flow_fields, total_fields, notes, watchlist: {item_id: name},
   watchlist_houses: {region: [house_id, ...]},
   regions: {us|eu: {
     hours: ["YYYY-MM-DDTHH:MMZ", ...]   every stored snapshot (UTC), oldest first; a missing hour is absent
     trading_day: ["YYYY-MM-DD", ...]    trading day of each snapshot (starts 12:00 UTC, named by its start)
     flow_hours: [h or null, ...]        hours since the previous snapshot, from flows; null = no flows yet
     houses: {house_id: faction},
     totals: {house_id: {<total_fields>: [...]}},          whole market, every house of the region
     items:  {house_id: {item_id: {<price_fields + flow_fields>: [...]}}}}}}   watchlist houses x items
  null = not known for that hour: the house is missing from that snapshot, the item isn't listed (prices),
  or flows aren't built yet (flow and sales fields). Never read null as zero.

Size (measured on a week of synthetic hours built from a live pull): ~50 KB per day for the US with the
seed watchlist (19 items x 2 houses, 12 houses): ~1.6 MB at 30 days, ~4.7 MB at 90.

Usage: python collector/pulse.py --out tools/analyst/pulse.json [--local DIR] [--regions us] [--since 2026-11-14]
                                 [--prev OLD.json [--recent-days 3]]
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

PRICE_FIELDS = ["min", "p10", "p25", "median", "quantity", "listings"]
FLOW_FIELDS = ["posted", "sold_est", "sold_clean", "expired", "suspect", "cancel_flag"]
TOTAL_FIELDS = ["listings", "units", "posted", "sold_est", "sold_clean", "value_est", "value_clean"]
HOURLY_COLS = ["snapshot", "house_id", "faction", "kind", "item_id", "variant", "listings", "quantity",
               "min_price", "p10_price", "p25_price", "median_price"]
FLOW_COLS = ["snapshot", "prev_snapshot", "hours_between", "house_id", "kind", "item_id", "variant",
             "new_units", "partial_units", "partial_value", "early_at_min", "early_within5", "relist_guess_units",
             "suspect_cheap_units", "expired_units", "gone_short_units", "gone_medium_units", "cancel_flag",
             "cur_min_price"]
NOTES = ("Times are UTC snapshot times (Blizzard's refresh, ~:17-:30 past the hour). Eastern = UTC-5 in winter "
         "(UTC-4 in summer). A trading day runs 12:00-12:00 UTC and is named by the date it starts (ADR 0014). "
         "Prices: copper per unit, quantity-weighted percentiles; quantity = units listed; listings = listings. "
         "Flows (#37) describe the hour ENDING at that snapshot, in units: posted = new units listed; sold_est = "
         "partial + early-vanished within 5% of the cheapest - relists (a low estimate: last-hour sales look like "
         "expiry); suspect = part of that which looks like cancels (#81); sold_clean = sold_est - suspect; expired = "
         "vanished after the listing's duration ran out; cancel_flag = 1 when suspect >= a quarter of the sale "
         "signal. Totals: listings and units listed across all items (incl. gear), and the same flows summed per "
         "house; value_* = copper value of sold_est / sold_clean (bought-out part at its own price, the rest at the "
         "previous hour's cheapest). Flows are built nightly at ~01:35 UTC per UTC day, so the newest ~12-36 hours "
         "have flow fields null until the next night's build.")


def trading_day(t: pd.Timestamp) -> str:
    return (t - pd.Timedelta(hours=12)).strftime("%Y-%m-%d")


def load_hourly(store, region: str, since: str, houses: set[int], ids: set[int], workers: int):
    """(totals per house x snapshot, watchlist rows, {house: faction}) from every hourly file since `since`."""
    keys = [k for k in list_keys(store, f"{prefix(region)}hourly/")
            if k.endswith(".parquet") and k.rsplit("/", 2)[1] >= since]

    def one(k):
        df = get_parquet(store, k, HOURLY_COLS)
        if df is None or not len(df):
            return None
        df["snapshot"] = pd.to_datetime(df["snapshot"], utc=True).dt.floor("min")   # = the raw/flows folder minute
        tot = df.groupby(["snapshot", "house_id"], as_index=False).agg(
            listings=("listings", "sum"), units=("quantity", "sum"), faction=("faction", "first"))
        w = df[df["house_id"].isin(houses) & df["item_id"].isin(ids) & (df["variant"] == "")]
        # an item sold both ways (rare for materials): keep the commodity row
        w = w.sort_values("kind").drop_duplicates(["snapshot", "house_id", "item_id"], keep="last")
        return tot, w.drop(columns=["faction", "kind", "variant"])

    with ThreadPoolExecutor(workers) as pool:   # R2 reads are slow one by one
        parts = [p for p in pool.map(one, keys) if p is not None]
    print(f"[{region}] {len(keys)} hourly files read")
    if not parts:
        return pd.DataFrame(), pd.DataFrame(), {}
    tot = pd.concat([p[0] for p in parts], ignore_index=True)
    w = pd.concat([p[1] for p in parts], ignore_index=True)
    fac = tot.drop_duplicates("house_id").set_index("house_id")["faction"].to_dict()
    return tot.drop(columns="faction"), w, fac


def day_before(key: str, since: str) -> bool:
    return key.rsplit("/", 1)[1][:10] < since


def load_flows(store, region: str, since: str, houses: set[int], ids: set[int]):
    """(totals per house x snapshot, watchlist rows per house x item x snapshot, hours_between per snapshot)."""
    keys = sorted(k for k in list_keys(store, f"{prefix(region)}flows/") if k.endswith(".parquet"))
    day0 = (pd.Timestamp(since) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")   # the day before: prev-hour prices
    keys = [k for k in keys if k.rsplit("/", 1)[1][:10] >= day0]
    tots, ws, hrs, carry = [], [], [], None
    for k in keys:
        f = get_parquet(store, k, FLOW_COLS)
        if f is None or not len(f):
            continue
        g = lambda c: f[c] if c in f else 0   # absent in files built before #69 / #81
        f["snapshot"] = pd.to_datetime(f["snapshot"], utc=True)
        for c in ("new_units", "partial_units", "partial_value", "early_at_min", "early_within5", "relist_guess_units"):
            f[c] = g(c)
        f["sold_est"] = (f["partial_units"] + f["early_at_min"] + f["early_within5"] - f["relist_guess_units"]).clip(lower=0)
        f["suspect"] = g("suspect_cheap_units")
        f["sold_clean"] = (f["sold_est"] - f["suspect"]).clip(lower=0)
        f["expired"] = g("expired_units") if "expired_units" in f else g("gone_short_units") + g("gone_medium_units")
        f["cancel_flag"] = g("cancel_flag")
        # value: units bought out of a listing that stayed up at their own price; the rest at the previous
        # hour's cheapest (early sales counted here vanished within 5% of it). Only rows with sales are joined.
        keys_ = ["house_id", "kind", "item_id", "variant"]
        sold = f[f["sold_est"] > 0].copy()
        if "cur_min_price" in f:
            book = f[keys_ + ["snapshot", "cur_min_price"]]
            pm = (book if carry is None else pd.concat([carry, book])).rename(
                columns={"snapshot": "prev_snapshot", "cur_min_price": "prev_min"})
            sold["prev_snapshot"] = pd.to_datetime(sold["prev_snapshot"], utc=True)
            sold = sold.merge(pm, on=keys_ + ["prev_snapshot"], how="left")
            carry = book[book["snapshot"] == book["snapshot"].max()]
            pmin = sold["prev_min"].fillna(0)
        else:
            carry, pmin = None, 0
        for c in ("sold_est", "sold_clean"):   # fewer units than the bought-out part (relists, cancels): scale it down
            part = (sold[c] / sold["partial_units"].where(sold["partial_units"] > 0)).clip(upper=1).fillna(0)
            sold[c.replace("sold", "value")] = sold["partial_value"] * part + (sold[c] - sold["partial_units"]).clip(lower=0) * pmin
        if day_before(k, since):
            continue   # read only for the previous hour's prices
        hrs.append(f.drop_duplicates("snapshot").set_index("snapshot")["hours_between"])
        t = f.rename(columns={"new_units": "posted"}).groupby(["snapshot", "house_id"])[["posted", "sold_est", "sold_clean"]].sum()
        t = t.join(sold.groupby(["snapshot", "house_id"])[["value_est", "value_clean"]].sum()).fillna(0)
        tots.append(t.reset_index())
        w = f[f["house_id"].isin(houses) & f["item_id"].isin(ids) & (f["variant"] == "")].rename(columns={"new_units": "posted"})
        ws.append(w.groupby(["snapshot", "house_id", "item_id"], as_index=False).agg(
            posted=("posted", "sum"), sold_est=("sold_est", "sum"), sold_clean=("sold_clean", "sum"),
            expired=("expired", "sum"), suspect=("suspect", "sum"), cancel_flag=("cancel_flag", "max")))
    print(f"[{region}] {len(keys)} flows files read")
    if not tots:
        return pd.DataFrame(), pd.DataFrame(), pd.Series(dtype=float)
    return pd.concat(tots, ignore_index=True), pd.concat(ws, ignore_index=True), pd.concat(hrs).sort_index()


def col(s: pd.Series) -> list:
    """Integers with None for unknown."""
    return [None if pd.isna(v) else int(round(v)) for v in s]


def build_region(store, region: str, since: str, houses: list[int], ids: set[int], workers: int) -> dict:
    hset = set(houses)
    tot, w, fac = load_hourly(store, region, since, hset, ids, workers)
    if not len(tot):
        return {"hours": [], "trading_day": [], "flow_hours": [], "houses": {}, "totals": {}, "items": {}}
    ftot, fw, fh = load_flows(store, region, since, hset, ids)
    snaps = sorted(tot["snapshot"].unique())
    idx = pd.DatetimeIndex(snaps)
    present = tot.set_index(["house_id", "snapshot"]).index   # house rows in each snapshot (a failed pull = absent)
    has_flow = idx.isin(fh.index)
    out = {"hours": [t.strftime("%Y-%m-%dT%H:%MZ") for t in idx],
           "trading_day": [trading_day(t) for t in idx],
           "flow_hours": [None if pd.isna(v) else round(float(v), 2) for v in fh.reindex(idx)],
           "houses": {str(h): fac[h] for h in sorted(fac)}, "totals": {}, "items": {}}
    ft = ftot.set_index(["house_id", "snapshot"]).sort_index() if len(ftot) else None
    for h, g in tot.groupby("house_id"):
        t = g.set_index("snapshot").reindex(idx)
        d = {"listings": col(t["listings"]), "units": col(t["units"])}
        for c in TOTAL_FIELDS[2:]:
            s = ft.loc[h][c].reindex(idx) if ft is not None and h in ft.index.get_level_values(0) else pd.Series(index=idx, dtype=float)
            s = s.where(~has_flow, s.fillna(0)).where(t["listings"].notna().values)   # flows built: no row = 0
            d[c] = col(s)
        out["totals"][str(h)] = d
    wi = w.set_index(["house_id", "item_id", "snapshot"]).sort_index() if len(w) else None
    fi = fw.set_index(["house_id", "item_id", "snapshot"]).sort_index() if len(fw) else None
    for h in houses:
        if h not in fac:
            continue
        here = pd.Series(idx.isin(present[present.get_level_values(0) == h].get_level_values(1)), index=idx)
        out["items"][str(h)] = {}
        for i in sorted(ids):
            p = wi.loc[(h, i)].reindex(idx) if wi is not None and (h, i) in wi.index.droplevel(2) else pd.DataFrame(index=idx, columns=HOURLY_COLS, dtype=float)
            q = fi.loc[(h, i)].reindex(idx) if fi is not None and (h, i) in fi.index.droplevel(2) else pd.DataFrame(index=idx, columns=FLOW_FIELDS, dtype=float)
            d = {}
            for f_, c in zip(PRICE_FIELDS, ["min_price", "p10_price", "p25_price", "median_price", "quantity", "listings"]):
                s = p[c].astype(float)
                if f_ in ("quantity", "listings"):
                    s = s.fillna(0)     # the house was pulled and the item wasn't there: none listed
                d[f_] = col(s.where(here))
            for c in FLOW_FIELDS:
                d[c] = col(q[c].astype(float).where(~has_flow, q[c].astype(float).fillna(0)).where(here))
            out["items"][str(h)][str(i)] = d
    n = len(idx)
    missing = int(round((idx[-1] - idx[0]) / pd.Timedelta(hours=1))) + 1 - n if n else 0
    print(f"[{region}] {n} snapshots {out['hours'][0]} .. {out['hours'][-1]} (~{missing} hours missing), "
          f"{len(out['totals'])} houses, {int(has_flow.sum())} hours with flows, "
          f"{sum(len(v) for v in out['items'].values())} watchlist series")
    return out


def merge(old: dict, new: dict) -> dict:
    """Region blocks combined hour by hour: the new read wins for every hour it has; hours only in the
    old export are kept as they were (never replace stored hours with nothing)."""
    hours = sorted(set(old["hours"]) | set(new["hours"]))
    oi = {h: i for i, h in enumerate(old["hours"])}
    ni = {h: i for i, h in enumerate(new["hours"])}

    def pick(oa, na):
        return [na[ni[h]] if na is not None and h in ni else oa[oi[h]] if oa is not None and h in oi else None
                for h in hours]

    def series(o: dict, n: dict) -> dict:
        return {f: pick(o.get(f), n.get(f)) for f in dict.fromkeys([*n, *o])}

    items = {}
    for h in dict.fromkeys([*new["items"], *old["items"]]):
        o, n = old["items"].get(h, {}), new["items"].get(h, {})
        items[h] = {i: series(o.get(i, {}), n.get(i, {})) for i in dict.fromkeys([*n, *o])}
    return {"hours": hours, "trading_day": [trading_day(pd.Timestamp(h)) for h in hours],
            "flow_hours": pick(old["flow_hours"], new["flow_hours"]),
            "houses": dict(sorted({**old["houses"], **new["houses"]}.items(), key=lambda kv: int(kv[0]))),
            "totals": {h: series(old["totals"].get(h, {}), new["totals"].get(h, {}))
                       for h in sorted({*old["totals"], *new["totals"]}, key=int)},
            "items": items}


def main() -> int:
    ap = argparse.ArgumentParser(description="Export every hour of watchlist and whole-market data (pulse switch)")
    ap.add_argument("--out", default="tools/analyst/pulse.json")
    ap.add_argument("--local", help="read this folder instead of R2")
    ap.add_argument("--regions", default=os.environ.get("PULSE_REGIONS", "us"))
    ap.add_argument("--since", default="2026-11-14", help="first UTC date to include")
    ap.add_argument("--watchlist", default=str(Path(__file__).resolve().parent.parent / "tools/analyst/watchlist.json"))
    ap.add_argument("--prev", help="the previous export: reuse its hours and re-read only the last --recent-days")
    ap.add_argument("--recent-days", type=int, default=3,
                    help="with --prev, UTC days re-read from storage (new hours, and flows built since the last run)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()
    store = LocalStore(Path(args.local)) if args.local else R2Store(os.environ.get("R2_BUCKET", "daytrader-data"))
    wl = json.loads(Path(args.watchlist).read_text())
    ids = {int(x["id"]) for x in wl["items"]}
    watch = {"watchlist": {str(x["id"]): x["name"] for x in wl["items"]},
             "watchlist_houses": {r: [int(h) for h in v] for r, v in wl.get("houses", {}).items()}}
    head = {"since": args.since, "price_fields": PRICE_FIELDS, "flow_fields": FLOW_FIELDS, "total_fields": TOTAL_FIELDS}
    prev = None
    if args.prev:
        try:
            prev = json.loads(Path(args.prev).read_text())
        except (OSError, ValueError) as e:
            print(f"No usable previous export ({type(e).__name__}); reading everything since {args.since}")
        # a changed watchlist, start date or field list needs every hour re-read
        if prev and any(prev.get(k) != v for k, v in {**head, **watch}.items() if k != "watchlist") \
                or prev and set(prev.get("watchlist", {})) != set(watch["watchlist"]):
            print("Previous export has a different watchlist, start date or fields; reading everything")
            prev = None
    read_from = args.since
    if prev:
        read_from = max(args.since, (datetime.now(timezone.utc) - pd.Timedelta(days=args.recent_days)).strftime("%Y-%m-%d"))
        print(f"Reusing {args.prev} (generated {prev.get('generated_at')}); re-reading from {read_from}")
    regions, failed = {}, False
    for r in [r.strip() for r in args.regions.split(",") if r.strip()]:
        old = (prev or {}).get("regions", {}).get(r)
        start = read_from if old else args.since          # a region new to the export: every hour
        new = build_region(store, r, start, watch["watchlist_houses"].get(r, []), ids, args.workers)
        if not new["hours"]:   # storage unreadable or the collector stopped: keep the old file, fail loudly
            print(f"! [{r}] no hourly files since {start}")
            failed = True
        regions[r] = merge(old, new) if old else new
    res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **head, "notes": NOTES,
           **watch, "regions": regions}
    text = json.dumps(res, separators=(",", ":"))
    if failed:
        return 1
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text + "\n")
    hours = ", ".join(f"{r} {len(v['hours'])} hours" for r, v in regions.items())
    print(f"Pulse export: {hours}, {len(text) / 1e6:.2f} MB -> {args.out} ({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

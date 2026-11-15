"""Listing flows (PonchoAndy/DayTrader#37, ADR 0008): what happened to listings between two hourly snapshots.

Matches listing IDs in consecutive raw pulls (raw/ is only kept 14 days, so this must run before it
expires) and writes one row per region × house × kind × item × variant × hour to
    [<region>/]flows/<YYYY-MM>/<YYYY-MM-DD>.parquet      (UTC date of the later snapshot; kept 90 days)

Per row (units unless noted; "prev" = the earlier snapshot, "cur" = the later one):
- hours_between, new_listings, new_units
- gone_{short,medium,long,very_long}_units: listings that vanished, by their last time-left bucket.
  LONG/VERY_LONG vanishings are "early" (sold or cancelled); SHORT/MEDIUM are probably expiries.
- partial_units, partial_value: units bought out of a listing that stayed up (certain sales), copper
- early_at_min / early_within5 / early_within20 / early_above: early-vanished units by price position
  against prev's cheapest unit price (where buyers actually buy)
- early_value: copper value of early vanishings, unit price capped at 2x prev's median
- relist_guess_units: early vanishings matched by a new listing of the same size at <= the price
- age_lt2h / age_2_12h / age_12_24h / age_24_48h / age_48h_plus: early-vanished units by how long the
  listing had been up (first seen -> last seen); first-seen times are carried across days in
  [<region>/]state/first_seen.parquet
- undercut_listings, undercut_units: new listings priced below prev's cheapest
- new_lot_lt1s / new_lot_1_10s / new_lot_10s_1g / new_lot_1_10g / new_lot_ge10g: new listings by
  total listing value (the deposit-change baseline), plus new_lot_sizes (distinct quantities)
- cur_min_price, depth_units_{2,5,10,25}, depth_gold_{2,5,10,25}: units and copper within +x% of cur's
  cheapest
- at_min_listings, at_min_lot_sizes (rough seller count): listings within 1% of cur's cheapest
- wall_units, wall_price: the largest single listing within 5% of cur's cheapest
- cur_tl_{short,medium,long,very_long}_units: time-left mix now (expiry waves)

Usage: python collector/flows.py [--regions us,eu] [--local DIR] [--day YYYY-MM-DD] [--max-days N]
Without --day it processes every complete UTC day in raw/ that has no flows file yet.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import LocalStore, R2Store, _loads, prefix, variant_key  # noqa: E402

TL = ["SHORT", "MEDIUM", "LONG", "VERY_LONG"]
KEYS = ["house_id", "kind", "item_id", "variant"]


def list_keys(store, pfx: str) -> list[str]:
    if isinstance(store, LocalStore):
        root = store.root
        return sorted(str(p.relative_to(root)) for p in (root / pfx).rglob("*") if p.is_file()) if (root / pfx).exists() else []
    out, token = [], None
    while True:
        kw = {"Bucket": store.bucket, "Prefix": pfx}
        if token:
            kw["ContinuationToken"] = token
        r = store.s3.list_objects_v2(**kw)
        out += [o["Key"] for o in r.get("Contents", [])]
        if not r.get("IsTruncated"):
            return out
        token = r["NextContinuationToken"]


def load_snapshot(store, keys: list[str]) -> pd.DataFrame:
    """All listings of one snapshot: id, house, kind, item, variant, qty, unit price, time-left."""
    import gzip
    cols = {c: [] for c in ["id", "house_id", "kind", "item_id", "variant", "qty", "price", "tl"]}
    for k in keys:
        name = k.rsplit("/", 1)[1]                      # house-113-auctions.json.gz
        _, hid, kind = name.split(".")[0].split("-")
        body = _loads(gzip.decompress(store.get(k)))
        for a in body.get("auctions") or []:
            q = a.get("quantity", 1) or 1
            p = a.get("unit_price") if kind == "commodities" else (a["buyout"] // q if a.get("buyout") else None)
            if p is None or "item" not in a:
                continue
            cols["id"].append(a["id"]); cols["house_id"].append(int(hid)); cols["kind"].append(kind)
            cols["item_id"].append(a["item"]["id"]); cols["variant"].append(variant_key(a["item"]))
            cols["qty"].append(q); cols["price"].append(p); cols["tl"].append(a.get("time_left", ""))
    df = pd.DataFrame(cols)
    return df.astype({"id": "int64", "house_id": "int16", "item_id": "int32", "qty": "int32", "price": "int64"})


def flows(prev: pd.DataFrame, cur: pd.DataFrame, first_seen: pd.Series, t_prev, t_cur) -> pd.DataFrame:
    hrs = (t_cur - t_prev).total_seconds() / 3600
    j = prev.merge(cur[["house_id", "kind", "id", "qty", "price"]], on=["house_id", "kind", "id"], how="left",
                   suffixes=("", "_cur"), indicator=True)
    gone = j[j["_merge"] == "left_only"].copy()
    stay = j[j["_merge"] == "both"]
    part = stay[stay["qty_cur"] < stay["qty"]].copy()
    part["pu"] = part["qty"] - part["qty_cur"]
    part["pv"] = part["pu"] * part["price"]
    newl = cur[~cur.set_index(["house_id", "kind", "id"]).index.isin(prev.set_index(["house_id", "kind", "id"]).index)].copy()

    # reference prices per item in prev / cur
    pref = prev.groupby(KEYS).agg(p_min=("price", "min"), p_med=("price", "median"))
    cmin = cur.groupby(KEYS)["price"].min().rename("c_min")

    out = []
    # gone by time-left
    g = gone.pivot_table(index=KEYS, columns="tl", values="qty", aggfunc="sum", fill_value=0)
    out.append(g.reindex(columns=TL, fill_value=0).rename(columns={t: f"gone_{t.lower()}_units" for t in TL}))
    early = gone[gone["tl"].isin(["LONG", "VERY_LONG"])].join(pref, on=KEYS)
    r = early["price"] / early["p_min"]
    early["pos"] = np.select([r <= 1.0001, r <= 1.05, r <= 1.20], ["early_at_min", "early_within5", "early_within20"], "early_above")
    out.append(early.pivot_table(index=KEYS, columns="pos", values="qty", aggfunc="sum", fill_value=0))
    early["val"] = early["qty"] * np.minimum(early["price"], 2 * early["p_med"])
    out.append(early.groupby(KEYS)["val"].sum().rename("early_value"))
    # listing age at vanishing (first seen -> last seen in prev)
    fs = early["id"].map(first_seen)
    age = (pd.Timestamp(t_prev) - pd.to_datetime(fs, utc=True)).dt.total_seconds() / 3600
    early["age"] = pd.cut(age.fillna(-1), [-np.inf, 0, 2, 12, 24, 48, np.inf],
                          labels=["age_unknown", "age_lt2h", "age_2_12h", "age_12_24h", "age_24_48h", "age_48h_plus"], right=False)
    out.append(early.pivot_table(index=KEYS, columns="age", values="qty", aggfunc="sum", fill_value=0, observed=False))
    # partial buys
    out.append(part.groupby(KEYS).agg(partial_units=("pu", "sum"), partial_value=("pv", "sum")))
    # new listings, undercuts, lot mix, relist guess
    newl = newl.join(pref, on=KEYS)
    newl["under"] = newl["price"] < newl["p_min"]
    lot = newl["qty"] * newl["price"]
    newl["lot"] = pd.cut(lot, [0, 100, 1000, 10000, 100000, np.inf], right=False,
                         labels=["new_lot_lt1s", "new_lot_1_10s", "new_lot_10s_1g", "new_lot_1_10g", "new_lot_ge10g"])
    out.append(newl.groupby(KEYS).agg(new_listings=("id", "size"), new_units=("qty", "sum"),
                                      undercut_listings=("under", "sum"), new_lot_sizes=("qty", "nunique")))
    out.append(newl[newl["under"]].groupby(KEYS)["qty"].sum().rename("undercut_units"))
    out.append(newl.pivot_table(index=KEYS, columns="lot", values="id", aggfunc="size", fill_value=0, observed=False))
    rl = early[KEYS + ["qty", "price"]].merge(newl[KEYS + ["qty", "price"]], on=KEYS + ["qty"], suffixes=("", "_n"))
    rl = rl[rl["price_n"] <= rl["price"]].drop_duplicates(KEYS + ["qty", "price"])
    out.append(rl.groupby(KEYS)["qty"].sum().rename("relist_guess_units"))
    # current book: depth, at-min crowding, wall, time-left mix
    c = cur.join(cmin, on=KEYS)
    rr = c["price"] / c["c_min"]
    for x in (2, 5, 10, 25):
        m = rr <= 1 + x / 100
        out.append(c[m].groupby(KEYS).agg(**{f"depth_units_{x}": ("qty", "sum")}))
        out.append((c[m]["qty"] * c[m]["price"]).groupby([c[m][k] for k in KEYS]).sum().rename(f"depth_gold_{x}"))
    am = c[rr <= 1.01]
    out.append(am.groupby(KEYS).agg(at_min_listings=("id", "size"), at_min_lot_sizes=("qty", "nunique")))
    w = c[rr <= 1.05].sort_values("qty", ascending=False).drop_duplicates(KEYS).set_index(KEYS)
    out.append(w[["qty", "price"]].rename(columns={"qty": "wall_units", "price": "wall_price"}))
    out.append(cmin.rename("cur_min_price"))
    tl = cur.pivot_table(index=KEYS, columns="tl", values="qty", aggfunc="sum", fill_value=0)
    out.append(tl.reindex(columns=TL, fill_value=0).rename(columns={t: f"cur_tl_{t.lower()}_units" for t in TL}))

    df = pd.concat(out, axis=1).fillna(0)
    df.columns = [str(c) for c in df.columns]
    df = df.reset_index()
    for col in df.columns:
        if col not in KEYS and col != "variant" and df[col].dtype.kind == "f":
            df[col] = df[col].round().astype("int64")
    df.insert(0, "hours_between", round(hrs, 2))
    df.insert(0, "prev_snapshot", pd.Timestamp(t_prev))
    df.insert(0, "snapshot", pd.Timestamp(t_cur))
    return df


def snapshots(store, pre: str) -> dict:
    """{snapshot datetime: [raw keys]} for every raw snapshot still in storage."""
    snaps = {}
    for k in list_keys(store, f"{pre}raw/"):
        snap = k.split("/")[-2]
        snaps.setdefault(snap, []).append(k)
    return {datetime.strptime(s, "%Y%m%dT%H%MZ").replace(tzinfo=timezone.utc): ks for s, ks in sorted(snaps.items())}


def run_region(store, region: str, days: list[str] | None, max_days: int) -> list[dict]:
    pre = prefix(region)
    snaps = snapshots(store, pre)
    times = sorted(snaps)
    done = {k.rsplit("/", 1)[1][:10] for k in list_keys(store, f"{pre}flows/")}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    todo = sorted({t.strftime("%Y-%m-%d") for t in times[1:]} - done - {today}) if not days else days
    todo = todo[:max_days]
    fs_raw = store.get(f"{pre}state/first_seen.parquet")
    first_seen = pd.read_parquet(io.BytesIO(fs_raw)).set_index("id")["first_seen"] if fs_raw else pd.Series(dtype="datetime64[ns, UTC]")
    logs = []
    for day in todo:
        t0 = time.time()
        pairs = [(a, b) for a, b in zip(times, times[1:]) if b.strftime("%Y-%m-%d") == day]
        rows, prev_df, prev_t = [], None, None
        for a, b in pairs:
            if prev_t != a:
                prev_df = load_snapshot(store, snaps[a])
                first_seen = pd.concat([first_seen, pd.Series(a, index=prev_df["id"][~prev_df["id"].isin(first_seen.index)].values)])
            cur_df = load_snapshot(store, snaps[b])
            first_seen = pd.concat([first_seen, pd.Series(b, index=cur_df["id"][~cur_df["id"].isin(first_seen.index)].values)])
            f = flows(prev_df, cur_df, first_seen, a, b)
            f.insert(1, "region", region)
            rows.append(f)
            prev_df, prev_t = cur_df, b
            first_seen = first_seen[first_seen.index.isin(cur_df["id"])]   # only listings still up
        if not rows:
            continue
        table = pd.concat(rows, ignore_index=True)
        buf = io.BytesIO(); table.to_parquet(buf, index=False, compression="zstd")
        store.put(f"{pre}flows/{day[:7]}/{day}.parquet", buf.getvalue())
        fsb = io.BytesIO(); first_seen.rename("first_seen").rename_axis("id").reset_index().to_parquet(fsb, index=False)
        store.put(f"{pre}state/first_seen.parquet", fsb.getvalue())
        log = {"region": region, "day": day, "pairs": len(pairs), "rows": len(table), "bytes": buf.tell(),
               "seconds": round(time.time() - t0, 1)}
        print(json.dumps(log)); logs.append(log)
    return logs


def main() -> int:
    ap = argparse.ArgumentParser(description="Listing flows from raw pulls (#37)")
    ap.add_argument("--regions", default=os.environ.get("REGIONS", "us,eu"))
    ap.add_argument("--local", help="read/write this folder instead of R2")
    ap.add_argument("--day", action="append", help="process this UTC day (repeatable); default: all missing complete days")
    ap.add_argument("--max-days", type=int, default=31)
    args = ap.parse_args()
    use_r2 = not args.local and all(os.environ.get(k) for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    store = R2Store(os.environ.get("R2_BUCKET", "daytrader-data")) if use_r2 else LocalStore(Path(args.local or "data/store"))
    t0 = time.time(); logs = []
    for region in [r.strip() for r in args.regions.split(",") if r.strip()]:
        logs += run_region(store, region, args.day, args.max_days)
    summary = {"finished": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1), "days": logs}
    store.put(f"runs/flows/{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json", json.dumps(summary, indent=1).encode(), "application/json")
    print(f"Flows done in {summary['seconds']} s: {len(logs)} region-days")
    return 0


if __name__ == "__main__":
    sys.exit(main())

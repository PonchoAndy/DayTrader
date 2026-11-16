"""Price history of crafting materials, exported for Claude sessions (which can't read R2).

Run by the workflow's "market" switch, which commits the output to the branch it was started from
(like the "health" and "demo" switches). Read-only on R2.

Reads, per region (US and EU, never mixed: house IDs repeat across regions, ADR 0009):
  [<region>/]hourly/<date>/*.parquet   every hourly summary still stored
  [<region>/]flows/<YYYY-MM>/<day>.parquet   listing flows (#37), if any
  items/items.parquet                  names and classes (shared)
and keeps crafting materials: item class Trade Goods or Reagent (also retail's names for them,
Tradeskill and Gem, for items named from retail's database), plus Miscellaneous items of subclass
Reagent (spell reagents). In WoW Forever gems such as Malachite are Trade Goods / Other. Both
commodities and auctions are kept (a few Trade Goods, e.g. rods and oils, are sold as auctions).

Vendor prices (sell_price = what a vendor pays you; purchase_price for purchase_quantity units) come
from Blizzard's static-forever-us item endpoint. They include Forever's own vendor-price changes
(Mild Spices sells for 1c there, 0c in retail; matches wago.tools' wowf ItemSparse). Item IDs are
permanent, so prices already in the previous export are reused, and only new items are looked up.
A failed lookup leaves the price empty; it never fails the export. (#70 will store these in R2.)

Output (JSON, compact; prices in copper per unit as integers, null = not listed that hour):
  {generated_at, fields, flow_fields, sampling, notes,
   items:   {item_id: {name, quality, class, subclass, kind, vendor_sell, vendor_buy, vendor_buy_qty}},
   regions: {us|eu: {snapshots: ["YYYY-MM-DDTHH:MMZ", ...],
                     houses: {house_id: faction},
                     series: {house_id: {item_id: [[min...], [p25...], [median...], [quantity...]]}},
                     flow_days: ["YYYY-MM-DD", ...], flow_hours: [hours covered per day],
                     flows: {house_id: {item_id: [[<flow_fields[0]> per day], ...]}}}}}

Size: about 73 KB per region per hour kept (~3.5 MB a day for US + EU). If the file would pass
--max-mb (default 8), it steps down LADDER until it fits: the newest 72 / 48 / 24 hours stay hourly and
older hours are thinned to every 3rd, 6th, 12th or 24th UTC hour; as a last resort house × item series
averaging under 10, then 25, listings an hour are dropped. `sampling` in the file says which step was used.
If even the last step is too big it is written anyway (GitHub accepts files up to 100 MB).

Usage: python collector/market.py --out tools/market/market.json [--local DIR] [--regions us,eu] [--days N]
"""
from __future__ import annotations

import argparse
import io
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

CLASSES = {"trade goods", "tradeskill", "gem", "reagent"}   # item_class names, lower-case
SUBCLASSES = {"reagent"}                                   # e.g. Miscellaneous / Reagent (not "Reagent Bag")
FIELDS = ["min", "p25", "median", "quantity"]
# (hours kept hourly, older hours every N h, min average listings per series), tried in order
LADDER = [(72, 1, 0), (72, 3, 0), (48, 3, 0), (48, 6, 0), (24, 6, 0), (24, 12, 0), (24, 24, 0),
          (24, 24, 10), (24, 24, 25)]
# Daily sums from flows.py (units). sold_est is the best guess at units bought:
#   partial (certain sales) + early_cheap (vanished early, within 5% of the cheapest) - relist
# "Early" = vanished before the listing could have expired (#69; flows from 2026-11-16 on; older days: with
# 2+ h left). early_short_medium = early units the old rule counted as expired. suspect = early_cheap units
# that look like cancels (#81), sold_clean = sold_est - suspect, cancel_flag = 1 when suspect is at least a
# quarter of partial + early_cheap. New fields go at the end so existing positions don't move.
FLOW_FIELDS = ["sold_est", "partial", "early_cheap", "early", "gone_short_medium", "relist", "new",
               "expired", "early_short_medium", "suspect", "sold_clean", "cancel_flag"]


def get_parquet(store, key: str, columns: list[str] | None = None) -> pd.DataFrame | None:
    raw = store.get(key)
    if raw is None:
        return None
    try:
        return pd.read_parquet(io.BytesIO(raw), columns=columns)
    except Exception:   # noqa: BLE001  (an older file without a column: read it whole)
        return pd.read_parquet(io.BytesIO(raw))


def materials(items: pd.DataFrame) -> pd.DataFrame:
    cls = items["item_class"].fillna("").str.lower()
    sub = items["item_subclass"].fillna("").str.lower()
    return items[cls.isin(CLASSES) | sub.isin(SUBCLASSES)]


def load_hourly(store, region: str, ids: set[int], workers: int, days: int = 0) -> pd.DataFrame:
    keys = [k for k in list_keys(store, f"{prefix(region)}hourly/") if k.endswith(".parquet")]
    if days:   # the folder name is the snapshot's UTC date
        since = (datetime.now(timezone.utc) - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
        keys = [k for k in keys if k.rsplit("/", 2)[1] >= since]
    cols = ["snapshot", "house_id", "faction", "kind", "item_id", "variant", "listings", "quantity",
            "min_price", "p25_price", "median_price"]

    def one(k):
        df = get_parquet(store, k, cols)
        if df is None:
            return None
        df = df[df["item_id"].isin(ids)]
        if "variant" in df:   # materials have no variants; keep the plain item only
            df = df[df["variant"] == ""]
        return df[[c for c in cols if c != "variant"]]

    with ThreadPoolExecutor(workers) as pool:   # R2 reads are slow one by one; ~2,200 files at 90 days
        frames = [f for f in pool.map(one, keys) if f is not None and len(f)]
    print(f"[{region}] {len(keys)} hourly files read")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols)


def load_flows(store, region: str, ids: set[int]) -> tuple[pd.DataFrame, pd.Series]:
    """Daily sums per house × item of the flow measures, and hours covered per day."""
    keys = [k for k in list_keys(store, f"{prefix(region)}flows/") if k.endswith(".parquet")]
    rows, hours = [], {}
    for k in keys:
        f = get_parquet(store, k)
        if f is None or not len(f):
            continue
        day = k.rsplit("/", 1)[1][:10]
        # hours covered: one value per snapshot pair (same for every house of the region)
        hours[day] = float(f.drop_duplicates("snapshot")["hours_between"].sum())
        f = f[f["item_id"].isin(ids) & (f["variant"] == "")]
        g = lambda c: f[c] if c in f else 0   # a column is absent when nothing of that kind happened that day
        gsm = g("gone_short_units") + g("gone_medium_units")
        new_rule = "early_units" in f           # flows built from 2026-11-16 on (#69)
        d = pd.DataFrame({"house_id": f["house_id"], "item_id": f["item_id"], "day": day,
                          "partial": g("partial_units"),
                          "early_cheap": g("early_at_min") + g("early_within5"),
                          "early": g("early_units") if new_rule else g("gone_long_units") + g("gone_very_long_units"),
                          "gone_short_medium": gsm,
                          "relist": g("relist_guess_units"), "new": g("new_units"),
                          "expired": g("expired_units") if new_rule else gsm,
                          "early_short_medium": g("early_short_medium_units"),
                          "suspect": g("suspect_cheap_units")})
        rows.append(d.groupby(["house_id", "item_id", "day"], as_index=False).sum())
    print(f"[{region}] {len(keys)} flows files read")
    if not rows:
        return pd.DataFrame(), pd.Series(dtype=float)
    t = pd.concat(rows, ignore_index=True)
    t["sold_est"] = (t["partial"] + t["early_cheap"] - t["relist"]).clip(lower=0)
    t["sold_clean"] = (t["sold_est"] - t["suspect"]).clip(lower=0)
    t["cancel_flag"] = ((t["suspect"] > 0) & (t["suspect"] >= 0.25 * (t["partial"] + t["early_cheap"]))).astype(int)
    return t, pd.Series(hours).sort_index()


def vendor_prices(ids: list[int], cached: dict) -> dict:
    """{item_id: (sell, buy, buy_qty)} from static-forever-us; cached values (previous export) reused."""
    out = {i: cached[i] for i in ids if i in cached and cached[i][0] is not None}
    todo = [i for i in ids if i not in out]
    if not todo:
        return out
    try:
        from blizzard import Api
        api = Api("us")

        def one(i):
            r = api.get(f"/data/wow/item/{i}", api.static)
            if not r.ok:
                return i, (None, None, None)
            b = r.json()
            return i, (b.get("sell_price"), b.get("purchase_price"), b.get("purchase_quantity"))

        with ThreadPoolExecutor(8) as pool:
            out.update(dict(pool.map(one, todo)))
    except Exception as e:  # noqa: BLE001  (no vendor prices is better than no export)
        print(f"! vendor price lookup failed: {type(e).__name__}: {e}"[:300])
    found = sum(1 for i in todo if (out.get(i) or (None,))[0] is not None)
    print(f"Vendor prices: {len(ids) - len(todo)} cached, {len(todo)} looked up, {found} found")
    return out


def nest(wide: dict[str, pd.DataFrame], keys) -> dict:
    """{house: {item: [row of each table]}} from tables indexed by (house_id, item_id), same columns."""
    lists = {f: dict(zip(t.index, t.astype(object).where(t.notna(), None).values.tolist())) for f, t in wide.items()}
    out = {}
    for hid, iid in keys:
        out.setdefault(str(hid), {})[str(iid)] = [lists[f][(hid, iid)] for f in wide]
    return out


def build_region(h: pd.DataFrame, fl: pd.DataFrame, fh: pd.Series, keep: list, min_listings: float = 0) -> dict:
    """One region's block. keep = the snapshots to include (after thinning); house × item series
    averaging fewer than min_listings listings per kept snapshot are left out (with their flows)."""
    h = h[h["snapshot"].isin(keep)]
    n = len(keep)
    out = {"snapshots": [pd.Timestamp(s).strftime("%Y-%m-%dT%H:%MZ") for s in keep],
           "houses": {str(k): v for k, v in sorted(h.drop_duplicates("house_id").set_index("house_id")["faction"].items())},
           "series": {}, "flow_days": [], "flow_hours": [], "flows": {}}
    if not len(h):
        return out
    listed = h.groupby(["house_id", "item_id"])["listings"].sum()
    kept = listed[listed >= min_listings * n].index if min_listings else listed.index
    h = h.set_index(["house_id", "item_id"]).loc[kept].reset_index()
    wide = {}
    for f, col in zip(FIELDS, ["min_price", "p25_price", "median_price", "quantity"]):
        t = h.pivot(index=["house_id", "item_id"], columns="snapshot", values=col).reindex(columns=keep)
        wide[f] = t.fillna(0).astype("int64") if f == "quantity" else t.astype("Int64")
    out["series"] = nest(wide, kept)
    if len(fl):
        days = list(fh.index)
        f = fl.set_index(["house_id", "item_id"])
        f = f[f.index.isin(kept)].reset_index()
        f = f[(f[FLOW_FIELDS] != 0).any(axis=1)]   # a day with nothing happening adds only zeros
        fw = {c: f.pivot(index=["house_id", "item_id"], columns="day", values=c).reindex(columns=days)
                  .fillna(0).astype("int64") for c in FLOW_FIELDS}
        fkeys = fw[FLOW_FIELDS[0]].index
        out.update(flow_days=days, flow_hours=[round(float(x), 2) for x in fh.values], flows=nest(fw, fkeys))
    return out


def thin(snaps: list, full_hours: float, every: int) -> list:
    """Keep every snapshot of the last full_hours; older ones only on UTC hours divisible by `every`."""
    if every <= 1 or not snaps:
        return snaps
    cutoff = max(snaps) - pd.Timedelta(hours=full_hours)
    return [s for s in snaps if s >= cutoff or pd.Timestamp(s).hour % every == 0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Export crafting-material price history (market switch)")
    ap.add_argument("--out", default="tools/market/market.json")
    ap.add_argument("--local", help="read this folder instead of R2")
    ap.add_argument("--regions", default=os.environ.get("REGIONS", "us,eu"))
    ap.add_argument("--max-mb", type=float, default=8.0)
    ap.add_argument("--days", type=int, default=0, help="only the last N days of hourly files (0 = all stored)")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    t0 = time.time()
    store = LocalStore(Path(args.local)) if args.local else R2Store(os.environ.get("R2_BUCKET", "daytrader-data"))
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]

    items = get_parquet(store, "items/items.parquet")
    if items is None:
        raise SystemExit("items/items.parquet not found")
    mats = materials(items)
    ids = set(mats["item_id"].astype(int))
    print(f"{len(ids)} crafting-material item IDs in items.parquet")

    data = {}
    for r in regions:
        h = load_hourly(store, r, ids, args.workers, args.days)
        fl, fh = load_flows(store, r, ids)
        data[r] = (h, fl, fh)
        print(f"[{r}] {len(h)} hourly rows, {h['snapshot'].nunique() if len(h) else 0} snapshots, "
              f"{h.groupby(['house_id', 'item_id']).ngroups if len(h) else 0} house×item series, {len(fh)} flow days")

    seen = sorted({int(i) for h, _, _ in data.values() for i in h["item_id"].unique()})
    meta = mats.set_index("item_id")
    kinds = pd.concat([h[["item_id", "kind"]] for h, _, _ in data.values()]).drop_duplicates()
    kind = kinds.groupby("item_id")["kind"].agg(lambda k: "/".join(sorted(k)))
    cached = {}
    try:
        old = json.loads(Path(args.out).read_text())
        cached = {int(k): (v.get("vendor_sell"), v.get("vendor_buy"), v.get("vendor_buy_qty"))
                  for k, v in old.get("items", {}).items()}
    except (OSError, ValueError):
        pass
    vendor = vendor_prices(seen, cached)
    items_out = {}
    for i in seen:
        m = meta.loc[i]
        sell, buy, bq = vendor.get(i, (None, None, None))
        items_out[str(i)] = {"name": m["name"], "quality": m["quality"], "class": m["item_class"],
                             "subclass": m["item_subclass"], "kind": kind.get(i), "vendor_sell": sell,
                             "vendor_buy": buy, "vendor_buy_qty": bq}

    notes = ("Prices: copper per unit (100 copper = 1 silver, 10000 = 1 gold); quantity = units listed; null = not "
             "listed that hour. Percentiles are quantity-weighted. Flows are units per UTC day, summed over the "
             "hours in flow_hours (24 = a full day). sold_est = partial + early_cheap - relist. Early = vanished before "
             "the listing could have expired, judged from its duration (2/8/24 h, #69); days built before 2026-11-16 "
             "used 'vanished with 2+ h left', which counted 2-hour listings' sales as expired. Sales in a listing's "
             "last hour still count as expired, so sold_est stays a low estimate; expired is the upper margin. "
             "suspect = early_cheap units that look like cancels (a commodity that vanished while a cheaper one "
             "stayed up, or a sudden batch pulled down whole, #81); sold_clean = sold_est - suspect; cancel_flag = 1 "
             "when suspect is at least a quarter of partial + early_cheap that day.")
    budget = args.max_mb * 1e6
    for full, every, min_l in LADDER:
        regions_out = {}
        for r, (h, fl, fh) in data.items():
            snaps = sorted(h["snapshot"].unique()) if len(h) else []
            regions_out[r] = build_region(h, fl, fh, thin(snaps, full, every), min_l)
        sampling = {"full_hours": full, "older_every_hours": every, "min_avg_listings": min_l, "max_mb": args.max_mb,
                    "days": args.days or "all"}
        res = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "fields": FIELDS, "flow_fields": FLOW_FIELDS, "sampling": sampling,
               "notes": notes, "items": items_out, "regions": regions_out}
        text = json.dumps(res, separators=(",", ":"))
        if len(text) <= budget:
            break
        last = (full, every, min_l) == LADDER[-1]
        print(f"{len(text) / 1e6:.1f} MB with {sampling}; over {args.max_mb} MB, "
              + ("writing it anyway" if last else "trying the next step"))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text + "\n")
    print(f"Market export: {len(items_out)} items, {sum(len(v['snapshots']) for v in regions_out.values())} "
          f"region-snapshots, sampling {sampling}, {len(text) / 1e6:.2f} MB -> {args.out} "
          f"({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

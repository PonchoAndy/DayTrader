"""Listing flows (PonchoAndy/DayTrader#37, ADR 0008): what happened to listings between two hourly snapshots.

Matches listing IDs in consecutive raw pulls (raw/ is only kept 14 days, so this must run before it
expires) and writes one row per region × house × kind × item × variant × hour to
    [<region>/]flows/<YYYY-MM>/<YYYY-MM-DD>.parquet      (UTC date of the later snapshot; kept 90 days)

Per row (units unless noted; "prev" = the earlier snapshot, "cur" = the later one):
- hours_between, new_listings, new_units
- gone_{short,medium,long,very_long}_units: listings that vanished, by their last time-left bucket.
- early_units / expired_units: vanished units split into "early" (sold or cancelled) and "probably
  expired" (#69). A listing's duration (2, 8 or 24 h) follows from its FIRST time-left bucket (MEDIUM,
  LONG, VERY_LONG; time-left labels: SHORT < 30 min, MEDIUM 30 min-2 h, LONG 2-12 h, VERY_LONG > 12 h).
  It was posted between the snapshot before its first sighting ("posted_after") and the first sighting,
  so it can't have expired before posted_after + duration: vanishing by then is early. Vanishing later
  counts as expired (it may still have been bought in its last hour; that stays invisible). Listings with
  an unknown start, first seen SHORT, or first seen after a gap of over 6 h use the old rule: early if
  last seen LONG/VERY_LONG. Before the 2026-11-16 code, "early" always meant the old rule, so a 2-hour
  listing's sales counted as expiries; files with an `early_units` column use the new rule.
- early_2h_units / early_8h_units / early_24h_units / early_unknown_dur_units: early units by duration
- early_short_medium_units: early units last seen SHORT/MEDIUM (the ones the old rule called expired)
- partial_units, partial_value: units bought out of a listing that stayed up (certain sales), copper
- early_at_min / early_within5 / early_within20 / early_above: early-vanished units by price position
  against prev's cheapest unit price (where buyers actually buy)
- early_value: copper value of early vanishings, unit price capped at 2x prev's median
- relist_guess_units: early vanishings matched by a new listing of the same size at <= the price
- age_lt2h / age_2_12h / age_12_24h / age_24_48h / age_48h_plus / age_unknown: early-vanished units by
  how long the listing had been up (first seen -> last seen); first-seen times are carried across days in
  [<region>/]state/first_seen.parquet (id, first_seen, posted_after, first_tl, burst)
  (early_*, age_* and relist_guess_units follow the early rule above, so they too include 2-hour
  listings from the 2026-11-16 code on.)
- Cancel check (#81): "sold" is inferred from early vanishing, so cancels that aren't reposted look like
  sales. Per early-vanished listing:
  - early_skipped_units (commodities only): a commodity buyer always gets the cheapest units first, so a
    listing that vanished while a cheaper one stayed up all hour wasn't bought.
  - early_burst_units: the listing was posted in a burst, an hour when the item got at least 3x its usual
    new units (trailing 24-hour hourly average, at least 6 hours of history) in at least 5 new listings.
  - early_batch_units: at least 3 lots with the same size, price and first-seen hour vanished together.
  - suspect_cancel_units: skipped, or burst AND batch (a batch that went up suddenly came down whole).
  - suspect_cheap_units: the suspects inside early_at_min + early_within5 (what sold estimates count),
    leaving out listings already matched as relists. A "clean" sold estimate is
    partial_units + early_at_min + early_within5 - relist_guess_units - suspect_cheap_units.
  - burst_units: new units this hour, if this hour was a burst for the item (else 0)
  - cancel_flag: 1 when suspect_cheap_units is at least a quarter of partial_units + early_at_min +
    early_within5 (this hour's sale signal is likely cancel noise)
- sale_max_price (from 2026-11-21): the highest unit price paid this hour, in copper: partial buys at their price,
  plus early vanishings within 20% of prev's cheapest that pass the cancel check and aren't relists; 0 = no sale
  seen. For commodities (cheapest units sell first) it shows how far up the book buyers climbed (the Ticker's wick).
- undercut_listings, undercut_units: new listings priced below prev's cheapest
- new_lot_lt1s / new_lot_1_10s / new_lot_10s_1g / new_lot_1_10g / new_lot_ge10g: new listings by
  total listing value (the deposit-change baseline), plus new_lot_sizes (distinct quantities)
- cur_min_price, depth_units_{2,5,10,25}, depth_gold_{2,5,10,25}: units and copper within +x% of cur's
  cheapest
- at_min_listings, at_min_lot_sizes (rough seller count): listings within 1% of cur's cheapest
- wall_units, wall_price: the largest single listing within 5% of cur's cheapest
- cur_tl_{short,medium,long,very_long}_units: time-left mix now (expiry waves)

Each day's log line (and runs/flows/*.json) also carries checks: new units by first time-left bucket
(H-D1/H-D3: MEDIUM well above zero means 2-hour listings are in use), `overlived` (listing-hours still
up after their implied duration; should be ~0, else the duration rule is wrong), and day totals of
early_short_medium_units and suspect_cheap_units.

Usage: python collector/flows.py [--regions us,eu] [--local DIR] [--day YYYY-MM-DD] [--max-days N] [--rebuild]
Without --day it processes every complete UTC day in raw/ that has no flows file yet. --rebuild redoes
every complete day still in raw/, oldest first, from an empty first-seen state (overwrites flows files).
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

# Early vs expired (#69): durations are 2/8/24 h, and the first time-left bucket tells which one.
DURATION_H = {"MEDIUM": 2, "LONG": 8, "VERY_LONG": 24}
SLACK_H = 0.25          # allows for the refresh minute drifting a few minutes between snapshots
MAX_FIRST_GAP_H = 6     # after a longer gap an 8 h listing can be first seen MEDIUM: duration unknown
# Cancel check (#81)
BURST_X, BURST_MIN_LISTINGS, BURST_MIN_HOURS, BURST_WINDOW = 3, 5, 6, 24
BATCH_MIN_LOTS = 3
FLAG_SHARE = 0.25
STATE_COLS = ["first_seen", "posted_after", "first_tl", "burst"]
FIXED_COLS = (["early_units", "expired_units", "early_2h_units", "early_8h_units", "early_24h_units",
               "early_unknown_dur_units", "early_short_medium_units", "early_at_min", "early_within5",
               "early_within20", "early_above", "early_skipped_units", "early_burst_units", "early_batch_units",
               "suspect_cancel_units", "suspect_cheap_units", "burst_units", "sale_max_price"])


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


def flows(prev: pd.DataFrame, cur: pd.DataFrame, state: pd.DataFrame, t_prev, t_cur,
          base: pd.Series, base_hours: int) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """One hour's flows. state: per listing id (index) first_seen, posted_after, first_tl, burst.
    base: trailing mean new units per hour per item (KEYS index) over base_hours hours.
    Returns the table, the ids of new listings posted in a burst, and day-log checks.

    Speed (#104): the ~40 group-bys run on one integer key instead of the four KEYS columns (two of them
    text), about 2-3x faster on a full US snapshot, so an hour fits in the hourly job. The key is each
    item's rank in KEYS order, so rows come out in the same order and the table is identical."""
    u = pd.concat([prev[KEYS], cur[KEYS]] + ([base.index.to_frame(index=False)] if len(base) else []), ignore_index=True)
    u = u.drop_duplicates().sort_values(KEYS, kind="mergesort").reset_index(drop=True)
    ix = pd.MultiIndex.from_frame(u)
    enc = lambda d: d.assign(gk=ix.get_indexer(pd.MultiIndex.from_frame(d[KEYS])))
    b2 = pd.Series(base.values, index=pd.Index(ix.get_indexer(base.index), name="gk")) if len(base) else base
    df, burst_ids, checks = _flows_core(enc(prev), enc(cur), state, t_prev, t_cur, b2, base_hours, ["gk"])
    keys = u.iloc[df["gk"].to_numpy()].reset_index(drop=True)
    pos = df.columns.get_loc("gk")
    df = df.drop(columns="gk")
    for n, k in enumerate(KEYS):
        df.insert(pos + n, k, keys[k].values)
    return df, burst_ids, checks


def _flows_core(prev: pd.DataFrame, cur: pd.DataFrame, state: pd.DataFrame, t_prev, t_cur,
                base: pd.Series, base_hours: int, K: list) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """One hour's flows. state: per listing id (index) first_seen, posted_after, first_tl, burst.
    base: trailing mean new units per hour per item (KEYS index) over base_hours hours.
    Returns the table, the ids of new listings posted in a burst, and day-log checks."""
    hrs = (t_cur - t_prev).total_seconds() / 3600
    j = prev.merge(cur[["house_id", "kind", "id", "qty", "price"]], on=["house_id", "kind", "id"], how="left",
                   suffixes=("", "_cur"), indicator=True)
    gone = j[j["_merge"] == "left_only"].join(state, on="id")
    stay = j[j["_merge"] == "both"]
    part = stay[stay["qty_cur"] < stay["qty"]].copy()
    part["pu"] = part["qty"] - part["qty_cur"]
    part["pv"] = part["pu"] * part["price"]
    newl = cur[~cur.set_index(["house_id", "kind", "id"]).index.isin(prev.set_index(["house_id", "kind", "id"]).index)].copy()

    # reference prices per item in prev / cur
    pref = prev.groupby(K).agg(p_min=("price", "min"), p_med=("price", "median"))
    cmin = cur.groupby(K)["price"].min().rename("c_min")

    out = []
    # gone by time-left
    g = gone.pivot_table(index=K, columns="tl", values="qty", aggfunc="sum", fill_value=0)
    out.append(g.reindex(columns=TL, fill_value=0).rename(columns={t: f"gone_{t.lower()}_units" for t in TL}))
    # early vs expired (#69): it can't have expired before posted_after + its duration
    t_cur_ts = pd.Timestamp(t_cur)
    since = (t_cur_ts - gone["posted_after"]).dt.total_seconds() / 3600
    gap = (gone["first_seen"] - gone["posted_after"]).dt.total_seconds() / 3600
    dur = gone["first_tl"].map(DURATION_H).where(gap <= MAX_FIRST_GAP_H)
    gone["dur"] = np.select([dur == 2, dur == 8, dur == 24], ["early_2h_units", "early_8h_units", "early_24h_units"],
                            "early_unknown_dur_units")
    gone["early"] = np.where(dur.notna(), since <= dur + SLACK_H, gone["tl"].isin(["LONG", "VERY_LONG"]))
    out.append(gone[~gone["early"]].groupby(K)["qty"].sum().rename("expired_units"))
    early = gone[gone["early"]].join(pref, on=K)
    out.append(early.groupby(K)["qty"].sum().rename("early_units"))
    out.append(early.pivot_table(index=K, columns="dur", values="qty", aggfunc="sum", fill_value=0))
    out.append(early[early["tl"].isin(["SHORT", "MEDIUM"])].groupby(K)["qty"].sum().rename("early_short_medium_units"))
    r = early["price"] / early["p_min"]
    early["pos"] = np.select([r <= 1.0001, r <= 1.05, r <= 1.20], ["early_at_min", "early_within5", "early_within20"], "early_above")
    out.append(early.pivot_table(index=K, columns="pos", values="qty", aggfunc="sum", fill_value=0))
    early["val"] = early["qty"] * np.minimum(early["price"], 2 * early["p_med"])
    out.append(early.groupby(K)["val"].sum().rename("early_value"))
    # listing age at vanishing (first seen -> last seen in prev)
    age = (pd.Timestamp(t_prev) - early["first_seen"]).dt.total_seconds() / 3600
    early["age"] = pd.cut(age.fillna(-1), [-np.inf, 0, 2, 12, 24, 48, np.inf],
                          labels=["age_unknown", "age_lt2h", "age_2_12h", "age_12_24h", "age_24_48h", "age_48h_plus"], right=False)
    out.append(early.pivot_table(index=K, columns="age", values="qty", aggfunc="sum", fill_value=0, observed=False))
    # partial buys
    out.append(part.groupby(K).agg(partial_units=("pu", "sum"), partial_value=("pv", "sum")))
    # new listings, undercuts, lot mix, relist guess
    newl = newl.join(pref, on=K)
    newl["under"] = newl["price"] < newl["p_min"]
    lot = newl["qty"] * newl["price"]
    newl["lot"] = pd.cut(lot, [0, 100, 1000, 10000, 100000, np.inf], right=False,
                         labels=["new_lot_lt1s", "new_lot_1_10s", "new_lot_10s_1g", "new_lot_1_10g", "new_lot_ge10g"])
    nk = newl.groupby(K).agg(new_listings=("id", "size"), new_units=("qty", "sum"),
                                undercut_listings=("under", "sum"), new_lot_sizes=("qty", "nunique"))
    out.append(nk)
    out.append(newl[newl["under"]].groupby(K)["qty"].sum().rename("undercut_units"))
    out.append(newl.pivot_table(index=K, columns="lot", values="id", aggfunc="size", fill_value=0, observed=False))
    rl = early[K + ["id", "qty", "price"]].merge(newl[K + ["qty", "price"]], on=K + ["qty"], suffixes=("", "_n"))
    rl = rl[rl["price_n"] <= rl["price"]]
    relisted = rl["id"].unique()
    rl = rl.drop_duplicates(K + ["qty", "price"])
    out.append(rl.groupby(K)["qty"].sum().rename("relist_guess_units"))

    # cancel check (#81)
    # bursts: this hour's new units >= 3x the item's trailing hourly mean, in >= 5 new listings
    burst_ids = np.array([], dtype="int64")
    if base_hours >= BURST_MIN_HOURS and len(nk):
        bb = nk[["new_listings", "new_units"]].join(base.rename("base"))
        bb = bb[(bb["new_listings"] >= BURST_MIN_LISTINGS) & (bb["new_units"] >= BURST_X * np.maximum(bb["base"].fillna(0), 1))]
        out.append(bb["new_units"].rename("burst_units"))
        burst_ids = newl.loc[newl.set_index(K).index.isin(bb.index), "id"].values
    # commodities: cheapest price among listings that stayed up all hour
    smin = stay[stay["kind"] == "commodities"].groupby(K)["price"].min().rename("s_min")
    early = early.join(smin, on=K)
    early["skip"] = early["price"] > early["s_min"]                  # NaN (no survivor) -> False
    early["burst"] = early["burst"].eq(True)
    lots = early.groupby(K + ["qty", "price", "first_seen"], dropna=True)["id"].transform("size")
    early["batch"] = lots.reindex(early.index).fillna(0) >= BATCH_MIN_LOTS
    early["suspect"] = early["skip"] | (early["burst"] & early["batch"])
    early["sus_cheap"] = (early["suspect"] & early["pos"].isin(["early_at_min", "early_within5"])
                          & ~early["id"].isin(relisted))
    fl = pd.DataFrame({c: early["qty"] * early[f] for c, f in [
        ("early_skipped_units", "skip"), ("early_burst_units", "burst"), ("early_batch_units", "batch"),
        ("suspect_cancel_units", "suspect"), ("suspect_cheap_units", "sus_cheap")]})
    out.append(fl.groupby([early[k] for k in K]).sum())

    # current book: depth, at-min crowding, wall, time-left mix
    c = cur.join(cmin, on=K)
    rr = c["price"] / c["c_min"]
    for x in (2, 5, 10, 25):
        m = rr <= 1 + x / 100
        out.append(c[m].groupby(K).agg(**{f"depth_units_{x}": ("qty", "sum")}))
        out.append((c[m]["qty"] * c[m]["price"]).groupby([c[m][k] for k in K]).sum().rename(f"depth_gold_{x}"))
    am = c[rr <= 1.01]
    out.append(am.groupby(K).agg(at_min_listings=("id", "size"), at_min_lot_sizes=("qty", "nunique")))
    w = c[rr <= 1.05].sort_values("qty", ascending=False).drop_duplicates(K).set_index(K)
    out.append(w[["qty", "price"]].rename(columns={"qty": "wall_units", "price": "wall_price"}))
    out.append(cmin.rename("cur_min_price"))
    tl = cur.pivot_table(index=K, columns="tl", values="qty", aggfunc="sum", fill_value=0)
    out.append(tl.reindex(columns=TL, fill_value=0).rename(columns={t: f"cur_tl_{t.lower()}_units" for t in TL}))

    # Highest price paid this hour (the Ticker's wick): units bought out of a listing that stayed up, at that
    # listing's price, plus early vanishings within 20% of prev's cheapest that pass the cancel checks and weren't
    # relisted. Commodity buyers take the cheapest units first, so this is how far up the book buyers climbed.
    # 0 = no sale seen. Added 2026-11-21; older files don't have the column.
    ok = early[~early["suspect"] & ~early["id"].isin(relisted) & early["pos"].ne("early_above")]
    paid = pd.concat([part[K + ["price"]], ok[K + ["price"]]])
    out.append(paid.groupby(K)["price"].max().rename("sale_max_price"))

    df = pd.concat(out, axis=1).fillna(0)
    df.columns = [str(c) for c in df.columns]
    for col in FIXED_COLS:                      # same columns every hour, even when nothing of a kind happened
        if col not in df:
            df[col] = 0
    df = df.reset_index()
    for col in df.columns:
        if col not in K and col != "variant" and df[col].dtype.kind == "f":
            df[col] = df[col].round().astype("int64")
    sale = df["partial_units"] + df["early_at_min"] + df["early_within5"]
    df["cancel_flag"] = ((df["suspect_cheap_units"] > 0) & (df["suspect_cheap_units"] >= FLAG_SHARE * sale)).astype("int8")
    df.insert(0, "hours_between", round(hrs, 2))
    df.insert(0, "prev_snapshot", pd.Timestamp(t_prev))
    df.insert(0, "snapshot", pd.Timestamp(t_cur))

    # checks for the day log: first time-left bucket of new listings (H-D1/H-D3)
    checks = {"new_units_first_tl": {k: int(v) for k, v in newl.groupby("tl")["qty"].sum().items()},
              "early_short_medium_units": int(df["early_short_medium_units"].sum()),
              "suspect_cheap_units": int(df["suspect_cheap_units"].sum())}
    return df, burst_ids, checks


def snapshots(store, pre: str) -> dict:
    """{snapshot datetime: [raw keys]} for every raw snapshot still in storage."""
    snaps = {}
    for k in list_keys(store, f"{pre}raw/"):
        snap = k.split("/")[-2]
        snaps.setdefault(snap, []).append(k)
    return {datetime.strptime(s, "%Y%m%dT%H%MZ").replace(tzinfo=timezone.utc): ks for s, ks in sorted(snaps.items())}


def load_state(raw: bytes | None) -> pd.DataFrame:
    """First-seen state per listing id. Files from before 2026-11-16 have only first_seen: their listings
    get an unknown posted_after / first_tl, so they're classified by the old rule (#69)."""
    st = pd.read_parquet(io.BytesIO(raw)).set_index("id") if raw else add_state(None, [])
    if "posted_after" not in st:
        st["posted_after"] = pd.Series(pd.NaT, index=st.index, dtype="datetime64[ns, UTC]")
        st["first_tl"] = pd.Series(None, index=st.index, dtype="object")
        st["burst"] = False
    return st[STATE_COLS]


def add_state(st: pd.DataFrame | None, ids, first_seen=None, posted_after=None, first_tl=None) -> pd.DataFrame:
    """Append listings first seen at first_seen (None = start unknown), posted after posted_after."""
    idx = pd.Index(ids, dtype="int64", name="id")
    ts = lambda t: pd.Series(pd.Timestamp(t) if t is not None else pd.NaT, index=idx, dtype="datetime64[ns, UTC]")
    new = pd.DataFrame({"first_seen": ts(first_seen), "posted_after": ts(posted_after),
                        "first_tl": pd.Series(first_tl, index=idx, dtype="object"),
                        "burst": pd.Series(False, index=idx, dtype="bool")}, index=idx)
    return new if st is None or not len(st) else pd.concat([st, new])


def new_checks() -> dict:
    return {"new_units_first_tl": {}, "overlived": 0, "early_short_medium_units": 0, "suspect_cheap_units": 0}


def step(prev_df: pd.DataFrame, cur_df: pd.DataFrame, state: pd.DataFrame, hist: list, a, b, region: str,
         checks: dict) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """One hour-pair (a -> b): the flows table, the updated first-seen state and burst history (#104).
    Uses nothing after b, so running it right after b is collected gives the nightly job's numbers."""
    nw = cur_df[~cur_df["id"].isin(state.index)]
    state = add_state(state, nw["id"].values, b, a, nw["tl"].values)
    base = (pd.concat(hist).groupby(KEYS)["new_units"].sum() / len(hist)) if hist else pd.Series(dtype=float)
    f, burst_ids, ck = flows(prev_df, cur_df, state, a, b, base, len(hist))
    if len(burst_ids):
        state.loc[state.index.isin(burst_ids), "burst"] = True
    f.insert(1, "region", region)
    hist = (hist + [f.loc[f["new_units"] > 0, KEYS + ["new_units"]]])[-BURST_WINDOW:]
    for k, v in ck["new_units_first_tl"].items():
        checks["new_units_first_tl"][k] = checks["new_units_first_tl"].get(k, 0) + v
    for k in ("early_short_medium_units", "suspect_cheap_units"):
        checks[k] += ck[k]
    state = state[state.index.isin(cur_df["id"])]   # only listings still up
    # data check: a listing still up after its implied duration means the duration rule is off (#69)
    sdur = state["first_tl"].map(DURATION_H).where(state["first_seen"] - state["posted_after"] <= pd.Timedelta(hours=MAX_FIRST_GAP_H))
    checks["overlived"] += int(((pd.Timestamp(b) - state["posted_after"]) > pd.to_timedelta(sdur + SLACK_H, unit="h")).sum())
    return f, state, hist


def run_region(store, region: str, days: list[str] | None, max_days: int, rebuild: bool = False) -> list[dict]:
    pre = prefix(region)
    snaps = snapshots(store, pre)
    times = sorted(snaps)
    done = {k.rsplit("/", 1)[1][:10] for k in list_keys(store, f"{pre}flows/")}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if rebuild:      # every complete day still in raw/, oldest first, from an empty state
        todo, done = sorted({t.strftime("%Y-%m-%d") for t in times[1:]} - {today}), set()
    else:
        todo = sorted({t.strftime("%Y-%m-%d") for t in times[1:]} - done - {today}) if not days else days
    todo = todo[:max_days]
    state = load_state(None if rebuild else store.get(f"{pre}state/first_seen.parquet"))
    hist: list[pd.DataFrame] = []          # last 24 hours' new units per item, for burst detection (#81)
    logs = []
    for day in todo:
        t0 = time.time()
        pairs = [(a, b) for a, b in zip(times, times[1:]) if b.strftime("%Y-%m-%d") == day]
        if not hist and not rebuild:       # seed the burst baseline from the previous day's flows
            pd_ = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            raw = store.get(f"{pre}flows/{pd_[:7]}/{pd_}.parquet")
            if raw:
                pf = pd.read_parquet(io.BytesIO(raw), columns=["snapshot"] + KEYS + ["new_units"])
                hist = [x[x["new_units"] > 0] for _, x in pf.groupby("snapshot")][-BURST_WINDOW:]
        rows, prev_df, prev_t = [], None, None
        checks = new_checks()
        for a, b in pairs:
            if prev_t != a:
                prev_df = load_snapshot(store, snaps[a])
                # Listings already up when this chain starts (no earlier processed hour) have an unknown
                # start; mark them NaT so they count as age_unknown, not as brand new.
                state = add_state(state, prev_df["id"][~prev_df["id"].isin(state.index)].values)
            cur_df = load_snapshot(store, snaps[b])
            f, state, hist = step(prev_df, cur_df, state, hist, a, b, region, checks)
            rows.append(f)
            prev_df, prev_t = cur_df, b
        if not rows:
            continue
        table = pd.concat(rows, ignore_index=True)
        buf = io.BytesIO(); table.to_parquet(buf, index=False, compression="zstd")
        store.put(f"{pre}flows/{day[:7]}/{day}.parquet", buf.getvalue())
        fsb = io.BytesIO(); state.reset_index().to_parquet(fsb, index=False)
        store.put(f"{pre}state/first_seen.parquet", fsb.getvalue())
        log = {"region": region, "day": day, "pairs": len(pairs), "rows": len(table), "bytes": buf.tell(),
               "seconds": round(time.time() - t0, 1), **checks}
        print(json.dumps(log)); logs.append(log)
    return logs


# --- Hourly flows (#104): one hour-pair right after each collection, same numbers as the nightly job ---
# [<region>/]flows-hourly/<YYYY-MM-DD>/<snapshot>.parquet   one hour (UTC date of the later snapshot)
# [<region>/]state/hourly/{meta.json, first_seen.parquet, hist.parquet, tail.parquet}
#   The hourly step's own state while it runs alongside the nightly job: the last processed snapshot (meta),
#   first-seen times, 24 pairs of new units (burst baseline) and the last snapshot's listings (tail), so the
#   next hour reads one small file instead of re-downloading the previous raw pull.
HOURLY_DIR, HSTATE = "flows-hourly", "state/hourly"
EST_PAIR_S = 20     # a US hour-pair: read the new raw pull, compare, write (~22 s measured 2026-11-20 before the
                    # one-key speed-up, ~18 s expected after; see each run's log in runs/flows-hourly/)


def _pq(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO(); df.to_parquet(buf, index=False, compression="zstd"); return buf.getvalue()


def recent_snapshots(store, pre: str, days_back: int = 2) -> dict:
    """Like snapshots(), but lists only the last few UTC days of raw/ (fast enough for the hourly job)."""
    snaps, today = {}, datetime.now(timezone.utc).date()
    for n in range(days_back, -1, -1):
        for k in list_keys(store, f"{pre}raw/{today - timedelta(days=n)}/"):
            snaps.setdefault(k.split("/")[-2], []).append(k)
    return {datetime.strptime(s, "%Y%m%dT%H%MZ").replace(tzinfo=timezone.utc): ks for s, ks in sorted(snaps.items())}


def hourly_region(store, region: str, deadline: float | None = None, full: bool = False) -> dict:
    """Process every snapshot after the last one done, oldest first, while time allows (deadline: a
    time.time() by which no new pair may start unless it can finish, est. EST_PAIR_S). full = list all of
    raw/ (catch-up after an outage, nightly job); otherwise only the last 2 UTC days."""
    t0, pre = time.time(), prefix(region)
    hs = f"{pre}{HSTATE}/"
    meta = json.loads(store.get(hs + "meta.json") or b"{}")
    snaps = snapshots(store, pre) if full else recent_snapshots(store, pre)
    log = {"region": region, "mode": "hourly", "pairs": 0, "written": []}
    if meta.get("tail"):
        a = datetime.fromisoformat(meta["tail"])
        if not full and snaps and a < min(snaps):
            snaps = snapshots(store, pre)             # fell behind more than 2 days: list everything
        state = load_state(store.get(hs + "first_seen.parquet"))
        h = store.get(hs + "hist.parquet")
        hd = pd.read_parquet(io.BytesIO(h)) if h else pd.DataFrame(columns=KEYS + ["new_units", "n"])
        by_n = {int(n): x.drop(columns="n") for n, x in hd.groupby("n")}
        empty = pd.DataFrame(columns=KEYS + ["new_units"])
        hist = [by_n.get(i, empty) for i in range(int(meta.get("hist_len", len(by_n))))]   # empty hours count too
        prev_df = pd.read_parquet(io.BytesIO(store.get(hs + "tail.parquet")))
    else:
        # First run: start where the nightly job stopped (its state is as of the last snapshot of its newest day)
        done = sorted(k.rsplit("/", 1)[1][:10] for k in list_keys(store, f"{pre}flows/") if k.endswith(".parquet"))
        if not done:
            log["status"] = "no nightly flows yet"; return log
        snaps = snapshots(store, pre)
        ends = [t for t in snaps if t.strftime("%Y-%m-%d") == done[-1]]
        if not ends:
            log["status"] = f"raw for {done[-1]} has expired"; return log
        a = max(ends)
        state = load_state(store.get(f"{pre}state/first_seen.parquet"))
        pf = pd.read_parquet(io.BytesIO(store.get(f"{pre}flows/{done[-1][:7]}/{done[-1]}.parquet")), columns=["snapshot"] + KEYS + ["new_units"])
        hist = [x.loc[x["new_units"] > 0, KEYS + ["new_units"]] for _, x in pf.groupby("snapshot")][-BURST_WINDOW:]
        prev_df = load_snapshot(store, snaps[a])
        state = add_state(state, prev_df["id"][~prev_df["id"].isin(state.index)].values)
        log["started_from"] = done[-1]
    checks = new_checks()
    for b in [t for t in sorted(snaps) if t > a]:
        if deadline is not None and time.time() + EST_PAIR_S > deadline:
            log["status"] = "stopped for time; the next run (or the nightly job) carries on"; break
        cur_df = load_snapshot(store, snaps[b])
        f, state, hist = step(prev_df, cur_df, state, hist, a, b, region, checks)
        key = f"{pre}{HOURLY_DIR}/{b:%Y-%m-%d}/{b:%Y%m%dT%H%MZ}.parquet"
        store.put(key, _pq(f))
        log["pairs"] += 1; log["written"].append(f"{b:%Y-%m-%dT%H:%MZ}")
        prev_df, a = cur_df, b
    if log["pairs"] or log.get("started_from"):
        store.put(hs + "first_seen.parquet", _pq(state.reset_index()))
        parts = [x[KEYS + ["new_units"]].assign(n=i) for i, x in enumerate(hist) if len(x)]
        store.put(hs + "hist.parquet", _pq(pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=KEYS + ["new_units", "n"])))
        store.put(hs + "tail.parquet", _pq(prev_df))
        store.put(hs + "meta.json", json.dumps({"tail": a.isoformat(), "hist_len": len(hist),
                                                "updated": datetime.now(timezone.utc).isoformat()}).encode(), "application/json")
    log.setdefault("status", "up to date" if log["pairs"] else "nothing new")
    log["tail"], log["seconds"] = f"{a:%Y-%m-%dT%H:%MZ}", round(time.time() - t0, 1)
    log["checks"] = checks
    return log


def compare_hourly(store, region: str, day: str) -> dict | None:
    """Check the parallel run (#104): the hourly files of a UTC day against the nightly file for it.
    Returns None when there are no hourly files for that day."""
    pre = prefix(region)
    keys = [k for k in list_keys(store, f"{pre}{HOURLY_DIR}/{day}/") if k.endswith(".parquet")]
    raw = store.get(f"{pre}flows/{day[:7]}/{day}.parquet")
    if not keys or not raw:
        return None
    night = pd.read_parquet(io.BytesIO(raw))
    hour = pd.concat([pd.read_parquet(io.BytesIO(store.get(k))) for k in keys], ignore_index=True)
    on = ["snapshot"] + KEYS
    for d in (night, hour):
        d["snapshot"] = pd.to_datetime(d["snapshot"], utc=True)
    hours_both = set(night["snapshot"]) & set(hour["snapshot"])
    n, h = (d[d["snapshot"].isin(hours_both)] for d in (night, hour))
    num = [c for c in n.columns if c in h.columns and c not in on and pd.api.types.is_numeric_dtype(n[c])]
    m = n.merge(h, on=on, how="outer", suffixes=("_n", "_h"), indicator=True)
    diff = {c: int(((m[f"{c}_n"].fillna(0) - m[f"{c}_h"].fillna(0)).abs() > 1e-6).sum()) for c in num}
    return {"region": region, "day": day, "hours_nightly": int(night["snapshot"].nunique()),
            "hours_hourly": int(hour["snapshot"].nunique()), "hours_compared": len(hours_both),
            "rows_only_nightly": int((m["_merge"] == "left_only").sum()), "rows_only_hourly": int((m["_merge"] == "right_only").sum()),
            "columns_differing": {c: v for c, v in diff.items() if v}, "match": not any(diff.values())
            and not (m["_merge"] != "both").any()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Listing flows from raw pulls (#37)")
    ap.add_argument("--regions", default=os.environ.get("REGIONS", "us,eu"))
    ap.add_argument("--local", help="read/write this folder instead of R2")
    ap.add_argument("--day", action="append", help="process this UTC day (repeatable); default: all missing complete days")
    ap.add_argument("--max-days", type=int, default=31)
    ap.add_argument("--rebuild", action="store_true",
                    help="redo every complete day still in raw/ from an empty first-seen state (overwrites flows)")
    ap.add_argument("--hourly", action="store_true", help="#104: process the newest hour(s) only (hourly job)")
    ap.add_argument("--budget", type=float, default=None,
                    help="with --hourly: start no hour-pair that would end later than this many seconds after the "
                         "job started (JOB_STARTED, set by the workflow)")
    ap.add_argument("--catch-up", action="store_true",
                    help="after the nightly build: compare each built day with the hourly files, then bring the "
                         "hourly state up to date (#104)")
    ap.add_argument("--hourly-regions", default=os.environ.get("HOURLY_REGIONS", "us"),
                    help="regions whose flows also run hourly (#104; US only until it has run a week)")
    args = ap.parse_args()
    use_r2 = not args.local and all(os.environ.get(k) for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    store = R2Store(os.environ.get("R2_BUCKET", "daytrader-data")) if use_r2 else LocalStore(Path(args.local or "data/store"))
    t0 = time.time(); logs = []
    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    if args.hourly:   # never fails the job: a missed hour is picked up by the next run or the nightly job
        job_t0 = float(os.environ.get("JOB_STARTED") or t0)
        deadline = job_t0 + args.budget if args.budget else None
        for region in regions:
            try:
                log = hourly_region(store, region, deadline)
            except Exception as e:  # noqa: BLE001
                log = {"region": region, "mode": "hourly", "status": f"error: {type(e).__name__}: {e}"}
            log["job_seconds"] = round(time.time() - job_t0, 1)
            print(json.dumps(log))
            store.put(f"{prefix(region)}runs/flows-hourly/{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json",
                      json.dumps(log).encode(), "application/json")
        return 0
    for region in regions:
        built = run_region(store, region, args.day, args.max_days, args.rebuild)
        logs += built
        if args.catch_up and region in args.hourly_regions.split(","):
            for lg in built:
                cmp = compare_hourly(store, region, lg["day"])
                if cmp:
                    print("Hourly vs nightly:", json.dumps(cmp)); lg["hourly_check"] = cmp
            hl = hourly_region(store, region, full=True)
            print(json.dumps(hl)); logs.append(hl)
    summary = {"finished": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1), "days": logs}
    store.put(f"runs/flows/{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json", json.dumps(summary, indent=1).encode(), "application/json")
    print(f"Flows done in {summary['seconds']} s: {len([x for x in logs if 'day' in x])} region-days")
    return 0


if __name__ == "__main__":
    sys.exit(main())

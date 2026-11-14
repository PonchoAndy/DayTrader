"""Read-only overview of what the collector has stored so far (prints to the log).

Run from GitHub Actions with the workflow's "report" switch, since R2 can't be read from
Claude's cloud sessions. Covers: run history, snapshot gaps, market size per snapshot, and
the biggest overnight moves on each faction's big houses.
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import R2Store  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 40)


def keys(store: R2Store, prefix: str) -> list[str]:
    out, token = [], None
    while True:
        kw = {"Bucket": store.bucket, "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        r = store.s3.list_objects_v2(**kw)
        out += [o["Key"] for o in r.get("Contents", [])]
        if not r.get("IsTruncated"):
            return out
        token = r["NextContinuationToken"]


def gold(copper: float) -> str:
    return f"{copper / 10000:,.2f}g"


def main() -> int:
    store = R2Store(os.environ.get("R2_BUCKET", "daytrader-data"))

    print("\n=== Runs ===")
    runs = [json.loads(store.get(k)) for k in sorted(keys(store, "runs/"))]
    rdf = pd.DataFrame(runs)
    cols = [c for c in ("started", "result", "snapshot", "seconds", "summary_rows", "gz_bytes") if c in rdf]
    print(rdf[cols].to_string(index=False))
    errs = [r for r in runs if r.get("errors")]
    print(f"{len(runs)} runs, {sum(r.get('result') == 'stored' for r in runs)} stored, "
          f"{sum(r.get('result') == 'no new data' for r in runs)} no-new-data, {len(errs)} with HTTP errors")
    if len(rdf):
        lag = (pd.to_datetime(rdf["started"]) - pd.to_datetime(rdf["newest_last_modified"])).dt.total_seconds() / 60
        print(f"Minutes from Blizzard's refresh to our pull: median {lag.median():.0f}, max {lag.max():.0f}")
        lm = pd.to_datetime(rdf["newest_last_modified"]).dt.minute
        print(f"Blizzard refresh minute past the hour: {sorted(lm.unique().tolist())}")

    print("\n=== Snapshots ===")
    files = sorted(keys(store, "hourly/"))
    frames = []
    for k in files:
        df = pd.read_parquet(io.BytesIO(store.get(k)))
        if "variant" not in df:
            continue  # early files merged variants; skip for comparability
        frames.append(df)
    print(f"{len(files)} hourly files, {len(frames)} with variants")
    want_demo = "--demo" in sys.argv
    if not frames:
        return 0
    t = pd.concat(frames, ignore_index=True)
    snaps = sorted(t["snapshot"].unique())
    gaps = pd.Series(snaps).diff().dt.total_seconds().div(3600).round(2)
    print(f"From {snaps[0]} to {snaps[-1]}; gaps between snapshots (hours): {gaps.dropna().value_counts().to_dict()}")

    names = pd.read_parquet(io.BytesIO(store.get("items/items.parquet")))[["item_id", "name", "item_class"]]
    bon = pd.read_parquet(io.BytesIO(store.get("items/bonuses.parquet")))[["bonus_id", "suffix"]]
    suffix = dict(zip(bon["bonus_id"].astype(str), bon["suffix"]))
    t = t.merge(names, on="item_id", how="left")
    t["name"] = t["name"].fillna("item " + t["item_id"].astype(str))
    t["label"] = t["name"] + t["variant"].map(lambda v: (" " + suffix.get(v, v)) if v else "")

    print("\n=== Market size per snapshot (all houses) ===")
    t["value"] = t["median_price"].clip(upper=10_000_000 * 100) * t["quantity"]  # cap absurd listings
    size = t.groupby(["snapshot", "faction"]).agg(listings=("listings", "sum"), value=("value", "sum")).reset_index()
    piv = size.pivot(index="snapshot", columns="faction", values="listings")
    print("Listings:\n" + piv.to_string())
    pv = size.pivot(index="snapshot", columns="faction", values="value").div(10000).round(0)
    print("Goods value (gold, median x quantity, capped):\n" + pv.to_string())

    print("\n=== Overnight moves, first vs last snapshot (big houses, commodities, >=200 units both times) ===")
    first, last = snaps[0], snaps[-1]
    for house in (113, 114, 110, 111):
        h = t[(t["house_id"] == house) & (t["kind"] == "commodities")]
        a = h[h["snapshot"] == first].set_index("label")[["quantity", "p10_price"]].add_suffix("_0")
        b = h[h["snapshot"] == last].set_index("label")[["quantity", "p10_price"]].add_suffix("_1")
        j = a.join(b, how="inner")
        j = j[(j["quantity_0"] >= 200) & (j["quantity_1"] >= 200) & (j["p10_price_0"] > 0)]
        j["price_change_%"] = ((j["p10_price_1"] / j["p10_price_0"] - 1) * 100).round(0)
        j["qty_change_%"] = ((j["quantity_1"] / j["quantity_0"] - 1) * 100).round(0)
        j["p10_then"] = j["p10_price_0"].map(gold)
        j["p10_now"] = j["p10_price_1"].map(gold)
        show = ["p10_then", "p10_now", "price_change_%", "quantity_0", "quantity_1", "qty_change_%"]
        fac = h["faction"].iloc[0] if len(h) else "?"
        print(f"\n-- House {house} ({fac}): {len(j)} items compared")
        print("Biggest price rises:\n" + j.sort_values("price_change_%", ascending=False).head(8)[show].to_string())
        print("Biggest price drops:\n" + j.sort_values("price_change_%").head(8)[show].to_string())
        print("Biggest supply drops (bought up?):\n" + j.sort_values("qty_change_%").head(8)[show].to_string())

    print("\n=== How steady are prices hour to hour? (house 113 commodities, items in every snapshot) ===")
    h = t[(t["house_id"] == 113) & (t["kind"] == "commodities")]
    present = h.groupby("label")["snapshot"].nunique()
    steady = h[h["label"].isin(present[present == len(snaps)].index)]
    swing = steady.groupby("label")["p10_price"].agg(lambda s: (s.max() / max(s.min(), 1) - 1) * 100)
    print(f"{len(present)} items seen, {len(swing)} in every snapshot. "
          f"Max/min p10 swing: median {swing.median():.0f}%, 75th pct {swing.quantile(.75):.0f}%, "
          f"90th pct {swing.quantile(.9):.0f}%")
    churn = h.groupby("snapshot")["label"].nunique()
    print("Distinct items listed per snapshot (house 113 commodities):\n" + churn.to_string())
    if want_demo:
        demo(t, snaps)
    return 0


def demo(t: pd.DataFrame, snaps: list) -> None:
    """Write a compact JSON of the overnight series for the demo page (`--demo <path>`), or print it."""
    big = [113, 114, 110, 111, 116, 117]
    c = t[t["kind"] == "commodities"]
    idx = {s: i for i, s in enumerate(snaps)}
    n = len(snaps)

    def series(df, col):
        out = [None] * n
        for s, v in zip(df["snapshot"], df[col]):
            out[idx[s]] = int(v)
        return out

    h = c[c["house_id"] == 113]
    first, last = snaps[0], snaps[-1]
    a = h[h["snapshot"] == first].set_index("label")
    b = h[h["snapshot"] == last].set_index("label")
    present = h.groupby("label")["snapshot"].nunique()
    ok = present[present >= n - 1].index
    j = a.loc[a.index.intersection(b.index).intersection(ok), ["quantity", "p10_price", "median_price"]].join(
        b[["quantity", "p10_price"]].add_suffix("_1"))
    j = j[j["p10_price"] >= 500]  # at least 5 silver, so % moves mean something
    pick = {}
    def add(labels, tag):
        for l in labels:
            pick.setdefault(l, []).append(tag)
    j["drain"] = 1 - j["quantity_1"] / j["quantity"]
    add(j[j["quantity"] >= 300].sort_values("drain", ascending=False).head(25).index, "demand")
    sw = h[h["label"].isin(j.index)].groupby("label")["p10_price"].agg(lambda s: s.max() / max(s.min(), 1))
    add(sw.sort_values(ascending=False).head(20).index, "volatile")
    j["value"] = j["median_price"] * j["quantity"]
    add(j.sort_values("value", ascending=False).head(25).index, "big market")
    al = c[(c["house_id"] == 110) & (c["snapshot"] == last)].set_index("label")["p10_price"]
    g = j.join(al.rename("p10_al"), how="inner")
    g["gap"] = (g[["p10_price_1", "p10_al"]].max(axis=1) / g[["p10_price_1", "p10_al"]].min(axis=1).clip(lower=1))
    add(g.sort_values("gap", ascending=False).head(20).index, "faction gap")

    meta = c.drop_duplicates("label").set_index("label")
    items = []
    for label, tags in pick.items():
        ser = {}
        for hid in big:
            d = c[(c["label"] == label) & (c["house_id"] == hid)]
            if len(d):
                ser[str(hid)] = {"p10": series(d, "p10_price"), "med": series(d, "median_price"), "qty": series(d, "quantity")}
        items.append({"label": label, "id": int(meta.loc[label, "item_id"]),
                      "cls": str(meta.loc[label, "item_class"]) if "item_class" in meta else "",
                      "tags": tags, "s": ser})
    supply = {}
    for (hid, fac), d in t.groupby(["house_id", "faction"]):
        tot = d.groupby("snapshot")["listings"].sum()
        supply[str(hid)] = {"faction": fac, "listings": [int(tot.get(s, 0)) for s in snaps]}
    out = json.dumps({"snapshots": [pd.Timestamp(s).isoformat() for s in snaps], "supply": supply, "items": items},
                     separators=(",", ":"))
    path = Path(sys.argv[sys.argv.index("--demo") + 1]) if len(sys.argv) > sys.argv.index("--demo") + 1 else None
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out)
        print(f"Demo data: {len(out)} chars, {len(items)} items -> {path}")
    else:
        print(out)


if __name__ == "__main__":
    sys.exit(main())

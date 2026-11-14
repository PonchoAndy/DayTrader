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
    if not frames:
        return 0
    t = pd.concat(frames, ignore_index=True)
    snaps = sorted(t["snapshot"].unique())
    gaps = pd.Series(snaps).diff().dt.total_seconds().div(3600).round(2)
    print(f"From {snaps[0]} to {snaps[-1]}; gaps between snapshots (hours): {gaps.dropna().value_counts().to_dict()}")

    names = pd.read_parquet(io.BytesIO(store.get("items/items.parquet")))[["item_id", "name"]]
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
    return 0


if __name__ == "__main__":
    sys.exit(main())

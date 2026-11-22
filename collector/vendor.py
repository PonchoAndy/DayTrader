"""Vendor prices for every item (PonchoAndy/DayTrader#70, #119).

What a vendor pays you (sell_price) and charges you (buy_price for buy_qty units), in copper. The deposit to
list an item is a share of sell_price (5/20/60% for 2/8/24 h at faction houses, 25/100/300% at Blackwater), so
every honest profit figure needs it; an item trading near its sell price is a floor marker (ADR 0018).

Source: the item table (`ItemSparse`) of the game's own data files, which wago.tools publishes per game
version, the same way bonuses.py reads them:
  1. WoW Forever (branch `wowf`): includes Forever's own changes (e.g. Mild Spices sells for 1c).
     Agrees with Blizzard's Forever API on all 2,153 items compared (Analyst, 2026-11-22).
  2. Classic Era (branch `wow_classic_era`) for items missing from Forever's files: ~2,950 traded items, mostly
     world-drop gear. Matched Forever's price on 83 of 85 sampled items. Labeled `classic_era`.
  ~300 items we've seen are in neither (no row; treat as unknown, never as 0).
Note: buy_price is set for nearly every item, including ones no vendor stocks; it does NOT mean a vendor
sells the item (see PLANNING, "Which items NPC vendors sell").

Stored as `items/vendor.parquet` (item_id, sell_price, buy_price, buy_qty, source, fetched_at), a separate file
from items.parquet so it's never rewritten by two jobs at once. Refreshed weekly by the hourly collector
(like bonuses.py, ~14 MB of downloads, a few seconds); a failure never affects collection.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

KEY = "items/vendor.parquet"
REFRESH_DAYS = 7
BRANCHES = [("forever", "wowf"), ("classic_era", "wow_classic_era")]   # first one wins
UA = {"User-Agent": "DayTrader-collector/0.1 (personal project)"}
COLUMNS = ["item_id", "sell_price", "buy_price", "buy_qty", "source", "fetched_at"]


def _rows(branch: str) -> list[dict]:
    r = requests.get(f"https://wago.tools/db2/ItemSparse/csv?branch={branch}", headers=UA, timeout=90)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def _int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def fetch() -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    seen, out = set(), []
    for source, branch in BRANCHES:
        rows = _rows(branch)
        if len(rows) < 1000:   # an error page or an empty table must not replace good data
            raise ValueError(f"wago.tools ItemSparse ({branch}) returned only {len(rows)} rows")
        for x in rows:
            i = _int(x.get("ID"), None)
            if i is None or i in seen:
                continue
            seen.add(i)
            out.append({"item_id": i, "sell_price": _int(x.get("SellPrice")), "buy_price": _int(x.get("BuyPrice")),
                        "buy_qty": max(1, _int(x.get("VendorStackCount"), 1)), "source": source, "fetched_at": now})
    t = pd.DataFrame(out, columns=COLUMNS).sort_values("item_id")
    for c in ("item_id", "sell_price", "buy_price", "buy_qty"):
        t[c] = t[c].astype("int64")
    return t


def load(store) -> pd.DataFrame:
    raw = store.get(KEY)
    return pd.read_parquet(io.BytesIO(raw)) if raw else pd.DataFrame(columns=COLUMNS)


def update(store, seen_ids: set[int] | None = None) -> dict:
    """Refresh the table if it's missing or older than REFRESH_DAYS. Reports coverage of the IDs seen."""
    table = load(store)
    age = (datetime.now(timezone.utc) - pd.to_datetime(table["fetched_at"], utc=True).max()) if len(table) else None
    refreshed = (not len(table)) or age > timedelta(days=REFRESH_DAYS)
    if refreshed:
        table = fetch()
        buf = io.BytesIO()
        table.to_parquet(buf, index=False, compression="zstd")
        store.put(KEY, buf.getvalue())
    out = {"refreshed": bool(refreshed), "total": len(table)}
    if refreshed and seen_ids:
        have = table[table["item_id"].isin(seen_ids)]
        out.update(seen=len(seen_ids), **{f"seen_{k}": int(v) for k, v in have["source"].value_counts().items()},
                   seen_missing=len(seen_ids) - len(have))
    return out


if __name__ == "__main__":   # local check: python collector/vendor.py
    t = fetch()
    print(t["source"].value_counts().to_dict())
    for i in (2678, 2589, 4306):   # Mild Spices 1c, Linen Cloth 13c, Silk Cloth 1s 50c (#70 spot check)
        print(t[t["item_id"] == i].to_dict("records"))

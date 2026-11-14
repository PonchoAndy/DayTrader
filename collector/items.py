"""Item names and basic metadata (PonchoAndy/DayTrader#27).

Item IDs are permanent, so each ID is looked up once and cached in a small table
(`items/items.parquet` in R2). Lookup order:
  1. WoW Forever's item database  (namespace static-forever-<region>)
  2. Retail WoW's item database   (namespace static-<region>); Forever uses the same item IDs,
     and its own database is incomplete (~half of IDs 404 there).
IDs found in neither are stored with source "missing" and retried after RETRY_MISSING_DAYS.

Columns: item_id, name, quality, item_class, item_subclass, inventory_type, source, checked_at
"""

from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd

from blizzard import Api

KEY = "items/items.parquet"
RETRY_MISSING_DAYS = 7
COLUMNS = ["item_id", "name", "quality", "item_class", "item_subclass", "inventory_type", "source", "checked_at"]


def _row(item_id: int, body: dict | None, source: str, now: datetime) -> dict:
    b = body or {}
    name = lambda k: (b.get(k) or {}).get("name") if isinstance(b.get(k), dict) else None
    return {
        "item_id": item_id,
        "name": b.get("name"),
        "quality": (b.get("quality") or {}).get("type"),          # e.g. COMMON, RARE, EPIC
        "item_class": name("item_class"),                          # e.g. Trade Goods, Armor
        "item_subclass": name("item_subclass"),                    # e.g. Herb, Cloth
        "inventory_type": (b.get("inventory_type") or {}).get("type"),
        "source": source,
        "checked_at": now,
    }


def lookup_one(api: Api, item_id: int, now: datetime) -> dict:
    for source, ns in (("forever", api.static), ("retail", f"static-{api.region}")):
        r = api.get(f"/data/wow/item/{item_id}", ns)
        if r.ok:
            return _row(item_id, r.json(), source, now)
    return _row(item_id, None, "missing", now)


def lookup_many(api: Api, item_ids: list[int], workers: int = 8) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(lambda i: lookup_one(api, i, now), item_ids))
    return pd.DataFrame(rows, columns=COLUMNS)


def load(store) -> pd.DataFrame:
    raw = store.get(KEY)
    return pd.read_parquet(io.BytesIO(raw)) if raw else pd.DataFrame(columns=COLUMNS)


def update(store, api: Api, seen_ids: set[int], limit: int = 4000) -> dict:
    """Look up IDs not in the table yet (plus stale 'missing' ones), up to `limit` per run."""
    table = load(store)
    known = set(table["item_id"].astype(int)) if len(table) else set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETRY_MISSING_DAYS)
    retry = set()
    if len(table):
        checked = pd.to_datetime(table["checked_at"], utc=True)
        retry = set(table.loc[(table["source"] == "missing") & (checked < cutoff), "item_id"].astype(int)) & seen_ids
    todo = sorted((seen_ids - known) | retry)[:limit]
    if not todo:
        return {"new": 0, "total": len(table)}
    found = lookup_many(api, todo)
    table = pd.concat([table[~table["item_id"].isin(found["item_id"])], found], ignore_index=True).sort_values("item_id")
    table["item_id"] = table["item_id"].astype("int64")
    buf = io.BytesIO()
    table.to_parquet(buf, index=False, compression="zstd")
    store.put(KEY, buf.getvalue())
    counts = found["source"].value_counts().to_dict()
    return {"new": len(todo), "total": len(table), "remaining": max(0, len((seen_ids - known) | retry) - len(todo)),
            "sources": {k: int(v) for k, v in counts.items()}}

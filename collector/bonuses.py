"""Names for item variants: bonus ID -> suffix ("of the Eagle") and stats (PonchoAndy/DayTrader#30).

Blizzard's API gives each auction's bonus IDs as bare numbers. The meaning lives in the game's own
data tables, which wago.tools publishes per game version. WoW Forever's version is the branch `wowf`.
  - ItemBonus: rows per bonus list (ParentItemBonusListID). Type 5 = name suffix, whose Value_0 is
    an ItemNameDescription ID; Type 2 = a stat bonus, Value_0 = stat type.
  - ItemNameDescription: ID -> text, e.g. "of the Eagle".

Stored as `items/bonuses.parquet` in R2 (bonus_id, suffix, stats, source_build, fetched_at) and
refreshed weekly, or sooner when the collector sees a bonus ID the table doesn't have.
Needs internet access to wago.tools, so it runs on GitHub Actions.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

KEY = "items/bonuses.parquet"
BRANCH = "wowf"  # WoW Forever on wago.tools
REFRESH_DAYS = 7
UA = {"User-Agent": "DayTrader-collector/0.1 (personal project)"}
COLUMNS = ["bonus_id", "suffix", "stats", "source_build", "fetched_at"]

# Item stat types used by bonus Type 2 rows (the game's ItemModType values; the common ones).
STATS = {0: "Mana", 1: "Health", 3: "Agility", 4: "Strength", 5: "Intellect", 6: "Spirit", 7: "Stamina",
         31: "Hit", 32: "Crit", 35: "Resilience", 36: "Haste", 37: "Expertise", 38: "Attack Power",
         43: "Mana Regen", 45: "Spell Power", 49: "Mastery"}


def _csv(table: str) -> list[dict]:
    r = requests.get(f"https://wago.tools/db2/{table}/csv?branch={BRANCH}", headers=UA, timeout=60)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def fetch() -> pd.DataFrame:
    bonus_rows = _csv("ItemBonus")
    names = {int(x["ID"]): x.get("Description_lang") or None for x in _csv("ItemNameDescription")}
    suffix, stats = {}, defaultdict(list)
    for x in bonus_rows:
        try:
            parent, typ, v0 = int(x["ParentItemBonusListID"]), int(x["Type"]), int(x["Value_0"])
        except (KeyError, ValueError):
            continue
        if typ == 5:
            suffix[parent] = names.get(v0)
        elif typ == 2:
            stats[parent].append(STATS.get(v0, f"stat {v0}"))
    now = datetime.now(timezone.utc)
    ids = sorted(set(suffix) | set(stats))
    return pd.DataFrame({"bonus_id": ids,
                         "suffix": [suffix.get(i) for i in ids],
                         "stats": [" + ".join(stats.get(i, [])) or None for i in ids],
                         "source_build": BRANCH,
                         "fetched_at": now}, columns=COLUMNS)


def load(store) -> pd.DataFrame:
    raw = store.get(KEY)
    return pd.read_parquet(io.BytesIO(raw)) if raw else pd.DataFrame(columns=COLUMNS)


def update(store, seen_bonus_ids: set[int]) -> dict:
    """Refresh the table if it's missing, older than REFRESH_DAYS, or lacks a bonus ID we've seen
    (but at most once a day for that last reason)."""
    table = load(store)
    known = set(table["bonus_id"].astype(int)) if len(table) else set()
    age = (datetime.now(timezone.utc) - pd.to_datetime(table["fetched_at"], utc=True).max()) if len(table) else None
    unknown = seen_bonus_ids - known
    due = (not len(table)) or age > timedelta(days=REFRESH_DAYS) or (unknown and age > timedelta(days=1))
    if not due:
        return {"refreshed": False, "total": len(table), "unknown_seen": len(unknown)}
    table = fetch()
    buf = io.BytesIO()
    table.to_parquet(buf, index=False, compression="zstd")
    store.put(KEY, buf.getvalue())
    still = seen_bonus_ids - set(table["bonus_id"].astype(int))
    named = table[table["bonus_id"].isin(seen_bonus_ids) & table["suffix"].notna()]
    return {"refreshed": True, "total": len(table), "seen": len(seen_bonus_ids),
            "seen_with_suffix": len(named), "seen_not_in_table": len(still),
            "examples": dict(zip(named["bonus_id"].astype(int).head(5), named["suffix"].head(5)))}

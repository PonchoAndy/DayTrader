"""Hourly auction collector (runs on GitHub Actions; see .github/workflows/collect.yml).

Each run:
1. Lists the auction houses of one ruleset and checks each house's Last-Modified time.
   If no house has new data since the last saved snapshot, it stops ("no new data").
2. Downloads auctions + commodities for every house and stores the raw responses, gzipped:
       raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<kind>.json.gz   (deleted after ~7 days by an R2 rule)
3. Writes one per-item summary table for the snapshot (Parquet):
       hourly/<YYYY-MM-DD>/<snapshot>.parquet
   One row per (house, kind, item): listings, total quantity, min / p10 / p25 / median / max unit price.
   Prices are in copper per unit (auctions: buyout ÷ quantity; bid-only auctions are skipped).
   Percentiles are weighted by quantity, so p10 = "the price of the cheapest 10% of units".
4. Saves a run log (runs/<YYYY-MM-DD>/<HHMMSS>.json) and state/latest.json.

<snapshot> is the newest Last-Modified time across houses, formatted YYYYMMDDTHHMMZ.

Storage: Cloudflare R2 when R2_ENDPOINT / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY are set
(bucket from R2_BUCKET, default daytrader-data); otherwise a local folder (--local, default data/store).

Usage: python collector/collect.py [--ruleset 2] [--region us] [--local DIR] [--force]
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd

from blizzard import Api, faction_of

ROOT = Path(__file__).resolve().parent.parent


# ---------- storage ----------
class LocalStore:
    def __init__(self, root: Path):
        self.root = root

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes | None:
        p = self.root / key
        return p.read_bytes() if p.exists() else None

    def where(self) -> str:
        return str(self.root)


def r2_endpoint(raw: str, bucket: str) -> str:
    """Tidy the R2_ENDPOINT secret: trim spaces/newlines, add https:// if missing, and drop a
    trailing /<bucket> path (Cloudflare shows the endpoint both with and without it)."""
    from urllib.parse import urlsplit

    v = raw.strip().strip('"').strip("'").strip()
    if "://" not in v:
        v = "https://" + v
    u = urlsplit(v)
    path = u.path.strip("/")
    # Describe the shape without revealing the value (GitHub masks it in logs anyway).
    print(f"R2 endpoint: scheme={u.scheme or '-'} host=*{(u.hostname or '')[-24:]} "
          f"path={'/' + path if path else '(none)'} length={len(raw)} had_whitespace={raw != raw.strip()}")
    if path == bucket:
        path = ""
    if not u.hostname or path:
        raise SystemExit("R2_ENDPOINT doesn't look like https://<account-id>.r2.cloudflarestorage.com "
                         "(see the shape above). Fix the GitHub secret and re-run.")
    return f"{u.scheme}://{u.netloc}"


class R2Store:
    def __init__(self, bucket: str):
        import boto3  # only needed when writing to R2

        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            endpoint_url=r2_endpoint(os.environ["R2_ENDPOINT"], bucket),
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes | None:
        try:
            return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.s3.exceptions.NoSuchKey:
            return None

    def where(self) -> str:
        return f"r2://{self.bucket}"


# ---------- summaries ----------
def listing_rows(body: dict, kind: str) -> list[tuple[int, int, int]]:
    """(item_id, quantity, unit_price) for each priced listing."""
    rows = []
    for a in body.get("auctions") or []:  # the field is missing entirely on empty houses
        qty = a.get("quantity", 1) or 1
        if kind == "commodities":
            price = a.get("unit_price")
        else:
            price = a["buyout"] // qty if a.get("buyout") else None
        if price is not None and "item" in a:
            rows.append((a["item"]["id"], qty, price))
    return rows


def summarize(rows: list[tuple[int, int, int]]) -> pd.DataFrame:
    """Per-item stats with quantity-weighted percentiles of unit price."""
    if not rows:
        return pd.DataFrame(columns=["item_id", "listings", "quantity", "min_price", "p10_price",
                                     "p25_price", "median_price", "max_price"])
    df = pd.DataFrame(rows, columns=["item_id", "qty", "price"]).sort_values(["item_id", "price"])
    g = df.groupby("item_id", sort=False)
    df["cum"] = g["qty"].cumsum()
    df["total"] = g["qty"].transform("sum")
    out = g.agg(listings=("qty", "size"), quantity=("qty", "sum"),
                min_price=("price", "min"), max_price=("price", "max"))
    for name, q in (("p10_price", 0.10), ("p25_price", 0.25), ("median_price", 0.50)):
        # first listing whose cumulative quantity reaches q of the item's total
        hit = df[df["cum"] >= q * df["total"]]
        out[name] = hit.groupby("item_id")["price"].first()
    return out.reset_index()[["item_id", "listings", "quantity", "min_price", "p10_price",
                              "p25_price", "median_price", "max_price"]]


# ---------- main ----------
def http_time(value: str | None) -> datetime | None:
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc) if value else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Hourly WoW Forever auction collector")
    ap.add_argument("--region", default=os.environ.get("BLIZZARD_REGION", "us"))
    ap.add_argument("--ruleset", type=int, default=2, help="2 = Normal (every ruleset currently returns the same houses)")
    ap.add_argument("--local", help="store in this folder instead of R2")
    ap.add_argument("--force", action="store_true", help="collect even if nothing changed since the last run")
    args = ap.parse_args()

    use_r2 = not args.local and all(os.environ.get(k) for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    store = R2Store(os.environ.get("R2_BUCKET", "daytrader-data")) if use_r2 else LocalStore(Path(args.local or ROOT / "data" / "store"))
    print(f"Storing to {store.where()}")

    started = datetime.now(timezone.utc)
    t0 = time.time()
    api = Api(args.region)
    houses = api.houses(args.ruleset)
    prev = json.loads(store.get("state/latest.json") or b"{}")

    # Pull everything first (a full pull takes ~15 s), then decide whether it's new.
    pulled = []  # (house, kind, response)
    for h in houses:
        for kind in ("auctions", "commodities"):
            r = api.house_listings(args.ruleset, h["id"], kind)
            pulled.append((h, kind, r))

    modified = {f"{h['id']}-{kind}": r.headers.get("last-modified") for h, kind, r in pulled if r.ok}
    newest = max((t for t in map(http_time, modified.values()) if t), default=started)
    snapshot = newest.strftime("%Y%m%dT%H%MZ")
    run = {"started": started.isoformat(), "region": args.region, "ruleset": args.ruleset,
           "snapshot": snapshot, "newest_last_modified": newest.isoformat(),
           "errors": {f"{h['id']}-{kind}": r.status_code for h, kind, r in pulled if not r.ok}}

    if not args.force and prev.get("last_modified") == modified:
        run.update(result="no new data", seconds=round(time.time() - t0, 1))
        print(f"No new data since snapshot {prev.get('snapshot')}; nothing stored.")
    else:
        day, hour = snapshot[:4] + "-" + snapshot[4:6] + "-" + snapshot[6:8], snapshot[9:11]
        frames, raw_bytes, gz_bytes = [], 0, 0
        for h, kind, r in pulled:
            if not r.ok:
                print(f"  ! house {h['id']} {kind}: HTTP {r.status_code}")
                continue
            gz = gzip.compress(r.content, compresslevel=6)
            store.put(f"raw/{day}/{hour}/{snapshot}/house-{h['id']}-{kind}.json.gz", gz, "application/gzip")
            raw_bytes += len(r.content)
            gz_bytes += len(gz)
            s = summarize(listing_rows(r.json(), kind))
            s.insert(0, "kind", kind)
            s.insert(0, "faction", faction_of(h.get("name", "")))
            s.insert(0, "house_id", h["id"])
            frames.append(s)

        table = pd.concat(frames, ignore_index=True)
        table.insert(0, "snapshot", pd.Timestamp(newest))
        table.insert(1, "region", args.region)
        for c in ("listings", "quantity", "min_price", "p10_price", "p25_price", "median_price", "max_price"):
            table[c] = table[c].astype("int64")
        buf = io.BytesIO()
        table.to_parquet(buf, index=False, compression="zstd")
        store.put(f"hourly/{day}/{snapshot}.parquet", buf.getvalue())

        run.update(result="stored", houses=len(houses), raw_bytes=raw_bytes, gz_bytes=gz_bytes,
                   summary_rows=len(table), summary_bytes=buf.tell(), seconds=round(time.time() - t0, 1))
        store.put("state/latest.json", json.dumps({"snapshot": snapshot, "last_modified": modified}, indent=1).encode(),
                  "application/json")
        print(f"Stored snapshot {snapshot}: {len(houses)} houses, {raw_bytes / 1e6:.1f} MB raw → "
              f"{gz_bytes / 1e6:.1f} MB gzipped; summary {len(table)} rows, {buf.tell() / 1e3:.0f} KB.")

    store.put(f"runs/{started:%Y-%m-%d}/{started:%H%M%S}.json", json.dumps(run, indent=1).encode(), "application/json")
    if run["errors"]:
        print(f"Errors: {run['errors']}")
    # Fail the run (so GitHub flags it) only if most of the pull failed.
    return 1 if len(run["errors"]) > len(pulled) // 2 else 0


if __name__ == "__main__":
    sys.exit(main())

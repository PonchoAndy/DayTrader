"""Hourly auction collector (runs on GitHub Actions; see .github/workflows/collect.yml).

Each run:
1. Lists the auction houses of one ruleset and checks each house's Last-Modified time.
   If no house has new data since the last saved snapshot, it stops ("no new data").
2. Downloads auctions + commodities for every house and stores the raw responses, gzipped:
       raw/<YYYY-MM-DD>/<HH>/<snapshot>/house-<id>-<kind>.json.gz   (deleted after ~7 days by an R2 rule)
3. Writes one per-item summary table for the snapshot (Parquet):
       hourly/<YYYY-MM-DD>/<snapshot>.parquet
   One row per (house, kind, item, variant): listings, total quantity, min / p10 / p25 / median / max
   unit price. `variant` = the listing's bonus IDs ("" if none), so "of the Monkey" and "of the Eagle"
   versions of an item are priced separately (#30). Summaries before 2026-11-14 03:xx lack it.
   Prices are in copper per unit (auctions: buyout ÷ quantity; bid-only auctions are skipped).
   Percentiles are weighted by quantity, so p10 = "the price of the cheapest 10% of units".
4. Names any item IDs it hasn't seen before (items/items.parquet, see items.py) and keeps the
   variant-name table current (items/bonuses.parquet, see bonuses.py).
5. Saves a run log (runs/<YYYY-MM-DD>/<HHMMSS>.json) with a "health" record (hours missed, houses
   empty or shrunken since the previous run, refresh minute; see health_record) and state/latest.json.

<snapshot> is the newest Last-Modified time across houses, formatted YYYYMMDDTHHMMZ.

Regions (ADR 0009): the US keeps the paths above; any other region gets the same layout under its own
prefix, e.g. eu/raw/..., eu/hourly/..., eu/runs/..., eu/state/latest.json. House IDs repeat across
regions, so a region's data must never share a path, state file or key with another's. Item and
variant names (items/) are shared and always looked up through the US API.

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

try:
    import orjson
    _loads = orjson.loads
except ImportError:  # local runs without orjson still work
    _loads = json.loads

from blizzard import Api, faction_of
import bonuses
import vendor
import items

ROOT = Path(__file__).resolve().parent.parent


# ---------- storage ----------
def prefix(region: str) -> str:
    """Storage prefix for a region: "" for the US (its original layout), "<region>/" otherwise."""
    return "" if region == "us" else f"{region}/"


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
def variant_key(item: dict) -> str:
    """Which version of an item a listing is: its bonus IDs, sorted and joined ("12749", "6654:1691").
    Empty for items without versions (and for all commodities). See #30."""
    bonus = item.get("bonus_lists") or []
    return ":".join(str(x) for x in sorted(bonus))


def listing_rows(body: dict, kind: str) -> list[tuple[int, str, int, int]]:
    """(item_id, variant, quantity, unit_price) for each priced listing."""
    rows = []
    for a in body.get("auctions") or []:  # the field is missing entirely on empty houses
        qty = a.get("quantity", 1) or 1
        if kind == "commodities":
            price = a.get("unit_price")
        else:
            price = a["buyout"] // qty if a.get("buyout") else None
        if price is not None and "item" in a:
            rows.append((a["item"]["id"], variant_key(a["item"]), qty, price))
    return rows


SUMMARY_COLUMNS = ["item_id", "variant", "listings", "quantity", "min_price", "p10_price",
                   "p25_price", "median_price", "max_price"]


def summarize(rows: list[tuple[int, str, int, int]]) -> pd.DataFrame:
    """Per item-version stats with quantity-weighted percentiles of unit price."""
    if not rows:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    keys = ["item_id", "variant"]
    df = pd.DataFrame(rows, columns=keys + ["qty", "price"]).sort_values(keys + ["price"])
    g = df.groupby(keys, sort=False)
    df["cum"] = g["qty"].cumsum()
    df["total"] = g["qty"].transform("sum")
    out = g.agg(listings=("qty", "size"), quantity=("qty", "sum"),
                min_price=("price", "min"), max_price=("price", "max"))
    for name, q in (("p10_price", 0.10), ("p25_price", 0.25), ("median_price", 0.50)):
        # first listing whose cumulative quantity reaches q of the version's total
        hit = df[df["cum"] >= q * df["total"]]
        out[name] = hit.groupby(keys)["price"].first()
    return out.reset_index()[SUMMARY_COLUMNS]


# ---------- main ----------
def http_time(value: str | None) -> datetime | None:
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc) if value else None
    except (TypeError, ValueError):
        return None


# ---------- health (a flag in the run log, never an error) ----------
# A house that had at least this many priced listings last time and now has under this share of
# them is flagged ("empty or shrunken"). Houses that are always empty (112/115/118) never reach
# the floor, so no house IDs are hard-coded.
HEALTH_MIN_PREVIOUS = 200
HEALTH_SHRINK = 0.25
HEALTH_GAP_HOURS = 1.5      # more than this between two stored snapshots = hours missed
HEALTH_STALE_MINUTES = 90   # "no new data" while Blizzard's newest data is older than this
HEALTH_DRIFT_MINUTES = 3    # refresh minute moved this much since the previous snapshot


def snapshot_time(snapshot: str) -> datetime:
    return datetime.strptime(snapshot, "%Y%m%dT%H%MZ").replace(tzinfo=timezone.utc)


def missed_hours(prev: datetime, new: datetime) -> list[str]:
    """UTC hours strictly between two snapshots' hours, e.g. 03:17 -> 06:17 gives 04 and 05."""
    a = prev.replace(minute=0, second=0, microsecond=0)
    b = new.replace(minute=0, second=0, microsecond=0)
    n = int((b - a).total_seconds() // 3600)
    return [(a + pd.Timedelta(hours=i)).strftime("%Y-%m-%dT%H") for i in range(1, n)]


def health_record(prev: dict, newest: datetime, started: datetime, has_last_modified: bool,
                  counts: dict | None, errors: dict) -> dict:
    """Health fields for one region's run (#18, #54). counts = listings per "<house>-<kind>" when the
    snapshot was stored, None for "no new data". Never raises: a health problem is a flag, not an error."""
    try:
        h = {"refresh_minute": newest.minute, "lag_minutes": round((started - newest).total_seconds() / 60),
             "flags": []}
        if not has_last_modified:
            h["flags"].append("no Last-Modified header from Blizzard (API change?)")
        if prev.get("snapshot"):
            p = snapshot_time(prev["snapshot"])
            if counts is not None:
                gap = (newest - p).total_seconds() / 3600
                h["gap_hours"] = round(gap, 2)
                h["missed_hours"] = missed_hours(p, newest)
                if gap > HEALTH_GAP_HOURS or h["missed_hours"]:
                    h["flags"].append(f"{len(h['missed_hours'])} hour(s) missed since {prev['snapshot']}")
            d = abs(newest.minute - p.minute)
            if counts is not None and min(d, 60 - d) >= HEALTH_DRIFT_MINUTES:
                h["flags"].append(f"refresh minute moved :{p.minute:02d} -> :{newest.minute:02d}")
        if counts is None and h["lag_minutes"] > HEALTH_STALE_MINUTES:
            h["flags"].append(f"no new data and Blizzard's newest is {h['lag_minutes']} min old")
        flagged = []
        for key, before in (prev.get("listings") or {}).items():
            if before < HEALTH_MIN_PREVIOUS or counts is None:
                continue
            if key in errors:
                flagged.append({"house": key, "listings": None, "previous": before, "reason": f"download {errors[key]}"})
            elif counts.get(key, 0) < HEALTH_SHRINK * before:
                flagged.append({"house": key, "listings": counts.get(key, 0), "previous": before,
                                "reason": "empty" if not counts.get(key) else "shrunk"})
        if flagged:
            h["houses_flagged"] = flagged
            h["flags"].append("houses empty or shrunken: " + ", ".join(f["house"] for f in flagged))
        h["ok"] = not h["flags"]
        return h
    except Exception as e:  # noqa: BLE001
        return {"ok": None, "error": f"{type(e).__name__}: {e}"[:200]}


CPU = IO = None   # process pool (gzip + summaries) and thread pool (uploads), set up in main()


def process_file(house_id: int, faction: str, kind: str, content: bytes, level: int):
    """CPU-heavy part for one response, run in a separate process: gzip it and summarize it.
    Returns (gzipped bytes, raw size, summary table)."""
    gz = gzip.compress(content, compresslevel=level)
    s = summarize(listing_rows(_loads(content), kind))
    s.insert(0, "kind", kind)
    s.insert(0, "faction", faction)
    s.insert(0, "house_id", house_id)
    return gz, len(content), s


def store_region(store, args, region: str, houses: list[dict], pulled: list, started: datetime, t0: float):
    """Decide whether a region's pull is new and, if so, store raw + summary + state. Returns (run, table)."""
    pre = prefix(region)
    prev = json.loads(store.get(f"{pre}state/latest.json") or b"{}")
    modified = {f"{h['id']}-{kind}": r.headers.get("last-modified") for h, kind, r in pulled if r is not None and r.ok}
    newest = max((t for t in map(http_time, modified.values()) if t), default=started)
    snapshot = newest.strftime("%Y%m%dT%H%MZ")
    run = {"started": started.isoformat(), "region": region, "ruleset": args.ruleset,
           "snapshot": snapshot, "newest_last_modified": newest.isoformat(),
           "errors": {f"{h['id']}-{kind}": (r.status_code if r is not None else "failed")
                      for h, kind, r in pulled if r is None or not r.ok}}
    has_lm = any(http_time(v) for v in modified.values())
    if not args.force and prev.get("last_modified") == modified:
        run.update(result="no new data", seconds=round(time.time() - t0, 1),
                   health=health_record(prev, newest, started, has_lm, None, run["errors"]))
        print(f"[{region}] No new data since snapshot {prev.get('snapshot')}; nothing stored.")
        return run, None

    day, hour = snapshot[:4] + "-" + snapshot[4:6] + "-" + snapshot[6:8], snapshot[9:11]
    frames, raw_bytes, gz_bytes, counts = [], 0, 0, {}
    ok = [(h, kind, r) for h, kind, r in pulled if r is not None and r.ok]
    for h, kind, r in pulled:
        if r is None or not r.ok:
            print(f"  ! [{region}] house {h['id']} {kind}: {getattr(r, 'status_code', 'failed')}")
    # gzip + summarize on every CPU core (GitHub's runners are ~3x slower than a laptop per core),
    # and upload the gzipped files on threads while the next ones are being processed.
    jobs = [CPU.submit(process_file, h["id"], faction_of(h.get("name", "")), kind, r.content, args.gzip_level)
            for h, kind, r in ok]
    puts = []
    for (h, kind, r), job in zip(ok, jobs):
        gz, n, s = job.result()
        raw_bytes += n
        gz_bytes += len(gz)
        frames.append(s)
        counts[f"{h['id']}-{kind}"] = int(s["listings"].sum())   # priced listings, for the health check
        puts.append(IO.submit(store.put, f"{pre}raw/{day}/{hour}/{snapshot}/house-{h['id']}-{kind}.json.gz", gz, "application/gzip"))
    for p in puts:
        p.result()   # an upload error fails the region, as before

    table = pd.concat(frames, ignore_index=True)
    table.insert(0, "snapshot", pd.Timestamp(newest))
    table.insert(1, "region", region)
    for c in ("listings", "quantity", "min_price", "p10_price", "p25_price", "median_price", "max_price"):
        table[c] = table[c].astype("int64")
    buf = io.BytesIO()
    table.to_parquet(buf, index=False, compression="zstd")
    store.put(f"{pre}hourly/{day}/{snapshot}.parquet", buf.getvalue())
    health = health_record(prev, newest, started, has_lm, counts, run["errors"])
    # A house that failed to download keeps last time's count, so the next run compares with real data.
    listings = {**{k: v for k, v in (prev.get("listings") or {}).items() if k in run["errors"]}, **counts}
    store.put(f"{pre}state/latest.json", json.dumps({"snapshot": snapshot, "last_modified": modified,
                                                     "listings": listings}, indent=1).encode(),
              "application/json")
    run.update(result="stored", houses=len(houses), raw_bytes=raw_bytes, gz_bytes=gz_bytes,
               summary_rows=len(table), summary_bytes=buf.tell(), seconds=round(time.time() - t0, 1),
               health=health)
    print(f"[{region}] Stored snapshot {snapshot}: {len(houses)} houses, {raw_bytes / 1e6:.1f} MB raw → "
          f"{gz_bytes / 1e6:.1f} MB gzipped; summary {len(table)} rows, {buf.tell() / 1e3:.0f} KB "
          f"({time.time() - t0:.1f} s since start).")
    return run, table


def main() -> int:
    ap = argparse.ArgumentParser(description="Hourly WoW Forever auction collector")
    ap.add_argument("--regions", default=os.environ.get("REGIONS") or os.environ.get("BLIZZARD_REGION", "us"),
                    help="comma-separated, in storing order; the first (us) is always stored first (ADR 0009)")
    ap.add_argument("--region", help="single region (same as --regions with one value)")
    ap.add_argument("--ruleset", type=int, default=2, help="2 = Normal (every ruleset currently returns the same houses)")
    ap.add_argument("--local", help="store in this folder instead of R2")
    ap.add_argument("--force", action="store_true", help="collect even if nothing changed since the last run")
    ap.add_argument("--skip-names", action="store_true", help="don't look up item/variant names (local tests)")
    ap.add_argument("--workers", type=int, default=8, help="downloads at once, across all regions")
    ap.add_argument("--deadline", type=float, default=120, help="seconds from start after which later regions are skipped")
    ap.add_argument("--gzip-level", type=int, default=1, help="raw-file compression: 1 is ~3x faster than 6, files ~25% bigger")
    args = ap.parse_args()
    regions = [args.region] if args.region else [r.strip() for r in args.regions.split(",") if r.strip()]

    use_r2 = not args.local and all(os.environ.get(k) for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))
    store = R2Store(os.environ.get("R2_BUCKET", "daytrader-data")) if use_r2 else LocalStore(Path(args.local or ROOT / "data" / "store"))
    print(f"Storing to {store.where()}; regions {regions}")

    started = datetime.now(timezone.utc)
    t0 = time.time()
    job_t0 = float(os.environ.get("JOB_STARTED") or t0)   # set by the workflow at the start of the job

    # 1. Start every download for every region at once (8 at a time), so one run covering
    #    several regions still fits in GitHub's one-minute billing unit (#54).
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait
    global CPU, IO
    import multiprocessing
    # "spawn": start clean worker processes rather than forking a process that already runs threads.
    CPU = ProcessPoolExecutor(max_workers=os.cpu_count() or 2, mp_context=multiprocessing.get_context("spawn"))
    IO = ThreadPoolExecutor(max_workers=8)
    pool = ThreadPoolExecutor(max_workers=args.workers)
    plans = []   # (region, api, houses, [(house, kind, future)])
    for region in regions:
        try:
            api = Api(region)
            houses = api.houses(args.ruleset)
        except Exception as e:  # noqa: BLE001  (a later region failing must not stop the first)
            print(f"! [{region}] couldn't list houses: {type(e).__name__}: {e}"[:300])
            plans.append((region, None, [], []))
            continue
        unknown = [h["id"] for h in houses if faction_of(h.get("name", "")) == "Unknown"]
        if unknown:
            print(f"! [{region}] houses with no recognisable faction: {unknown}")
        futs = [(h, kind, pool.submit(api.house_listings, args.ruleset, h["id"], kind))
                for h in houses for kind in ("auctions", "commodities")]
        plans.append((region, api, houses, futs))

    # 2. Store region by region, in order: the US is stored before anything else is looked at.
    runs, tables, bad = [], [], False
    for i, (region, api, houses, futs) in enumerate(plans):
        if api is None:
            runs.append({"started": started.isoformat(), "region": region, "result": "failed", "errors": {"houses": "failed"},
                         "health": {"ok": False, "flags": ["couldn't list houses"]}})
            bad = True
            continue
        timeout = None if i == 0 else max(0.0, args.deadline - (time.time() - job_t0))
        done, pending = wait([f for _, _, f in futs], timeout=timeout)
        if pending:
            for f in pending:
                f.cancel()
            print(f"! [{region}] {len(pending)} downloads not finished by the {args.deadline:.0f} s deadline; skipped this hour")
            runs.append({"started": started.isoformat(), "region": region, "result": "deadline", "errors": {},
                         "pending": len(pending),
                         "health": {"ok": False, "flags": [f"skipped: not downloaded by the {args.deadline:.0f} s deadline"]}})
            continue
        pulled = []
        for h, kind, f in futs:
            try:
                pulled.append((h, kind, f.result()))
            except Exception as e:  # noqa: BLE001
                print(f"  ! [{region}] house {h['id']} {kind}: {type(e).__name__}")
                pulled.append((h, kind, None))
        try:
            run, table = store_region(store, args, region, houses, pulled, started, t0)
        except Exception as e:  # noqa: BLE001  (a later region failing must not undo the first)
            if i == 0:
                raise
            print(f"! [{region}] storing failed: {type(e).__name__}: {e}"[:300])
            run, table = {"started": started.isoformat(), "region": region, "result": "failed",
                          "errors": {"store": f"{type(e).__name__}"},
                          "health": {"ok": False, "flags": ["storing failed"]}}, None
        runs.append(run)
        if table is not None:
            tables.append(table)
        if len(run.get("errors", {})) > max(len(pulled), 1) // 2:
            bad = True
    pool.shutdown(wait=False, cancel_futures=True)
    CPU.shutdown(wait=True)
    IO.shutdown(wait=True)

    # 3. Names, once for every region's items. IDs are permanent and shared across regions, so they
    #    are always looked up through the US API. A failure here must not lose stored snapshots.
    names = {}
    if tables and not args.skip_names:
        ids = set().union(*(set(t["item_id"].astype(int)) for t in tables))
        try:
            names["items"] = items.update(store, Api("us"), ids, limit=8000)
            print(f"Items: {names['items']}")
        except Exception as e:  # noqa: BLE001
            names["items"] = {"error": f"{type(e).__name__}: {e}"[:300]}
            print(f"Item lookup failed: {names['items']['error']}")
        try:
            seen_bonus = {int(b) for t in tables for v in t["variant"].unique() if v for b in v.split(":")}
            names["bonuses"] = bonuses.update(store, seen_bonus)
            print(f"Bonuses: {names['bonuses']}")
        except Exception as e:  # noqa: BLE001
            names["bonuses"] = {"error": f"{type(e).__name__}: {e}"[:300]}
            print(f"Bonus lookup failed: {names['bonuses']['error']}")
        try:   # vendor prices (#70): weekly, from the game's data files on wago.tools
            names["vendor"] = vendor.update(store, ids)
            if names["vendor"].get("refreshed"):
                print(f"Vendor prices: {names['vendor']}")
        except Exception as e:  # noqa: BLE001
            names["vendor"] = {"error": f"{type(e).__name__}: {e}"[:300]}
            print(f"Vendor price lookup failed: {names['vendor']['error']}")

    # 4. Run logs, one per region, each with the whole job's duration (job_seconds) for the
    #    one-minute check (#54: median <= 45 s, 95% <= 55 s).
    job_seconds = round(time.time() - job_t0, 1)
    for run in runs:
        run["job_seconds"] = job_seconds
        run["regions_in_job"] = regions
        if run.get("region") == regions[0]:
            run.update(names)
        pre = prefix(run["region"])
        store.put(f"{pre}runs/{started:%Y-%m-%d}/{started:%H%M%S}.json", json.dumps(run, indent=1).encode(), "application/json")
        if run.get("errors"):
            print(f"[{run['region']}] errors: {run['errors']}")
        hl = run.get("health") or {}
        print(f"[{run['region']}] health: " + ("ok" if hl.get("ok") else "; ".join(hl.get("flags") or [hl.get("error", "?")]))
              + (f" (refresh :{hl['refresh_minute']:02d}, gap {hl.get('gap_hours', '-')} h)" if "refresh_minute" in hl else ""))
    print(f"Job time so far: {job_seconds} s")
    return 1 if bad else 0


if __name__ == "__main__":
    code = main()
    # Exit at once: downloads skipped by the deadline may still be running on worker threads, and
    # waiting for them would keep the GitHub job (and its billed minutes) going. Everything that
    # matters is already stored by now.
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(code)

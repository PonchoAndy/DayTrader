"""Read DayTrader's R2 storage from a Claude cloud session (read-only).

Claude sessions can't use the collector's S3 keys (they're GitHub Actions secrets). Instead the
DayTrader cloud environment holds a read-only Cloudflare API token (permission "Workers R2 Storage:
Read") as a network secret for api.cloudflare.com: the session's proxy adds it to every request, so
no key is needed here and none is ever in a file (ADR 0016). This script uses Cloudflare's REST API
for R2, so it works only inside such a session.

Usage (from the repo root):
  python tools/r2read.py ls [PREFIX]                 list folders and files under PREFIX ("" = top)
  python tools/r2read.py get KEY [-o FILE]           download one file (default: into the cache)
  python tools/r2read.py sync PREFIX [--since DAY]   download every file under PREFIX into the cache
                                                     (skips files already there; --since YYYY-MM-DD
                                                     keeps only day folders/files on or after DAY)

Cache: $R2_CACHE or /tmp/r2cache, mirroring the bucket's paths (e.g. /tmp/r2cache/hourly/2026-11-22/...).
From Python:  sys.path.insert(0, "tools"); from r2read import read_parquet, ls, fetch
  read_parquet("items/items.parquet")  -> pandas DataFrame (cached after the first read)

Layout of the bucket (what each folder holds): collector/README.md, "Storage layout".
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://api.cloudflare.com/client/v4"
BUCKET = os.environ.get("R2_BUCKET", "daytrader-data")
CACHE = Path(os.environ.get("R2_CACHE", "/tmp/r2cache"))
_s = requests.Session()


def _check(r: requests.Response) -> requests.Response:
    if r.status_code in (401, 403):
        raise SystemExit(
            f"R2 read refused ({r.status_code}). This needs a Claude cloud session in the DayTrader "
            "environment, whose network secret for api.cloudflare.com is a token with "
            "'Workers R2 Storage: Read'. Details: ADR 0016.")
    r.raise_for_status()
    return r


@lru_cache(maxsize=1)
def account_id() -> str:
    if os.environ.get("CF_ACCOUNT_ID"):
        return os.environ["CF_ACCOUNT_ID"]
    res = _check(_s.get(f"{API}/accounts", timeout=30)).json()["result"]
    if not res:
        raise SystemExit("The token can't see any Cloudflare account.")
    return res[0]["id"]


def _objects_url(key: str = "") -> str:
    base = f"{API}/accounts/{account_id()}/r2/buckets/{BUCKET}/objects"
    return f"{base}/{quote(key)}" if key else base


def ls(prefix: str = "", delimiter: str | None = "/") -> tuple[list[str], list[dict]]:
    """(sub-folders, files) directly under prefix; with delimiter=None, every file below it."""
    folders: list[str] = []
    files: list[dict] = []
    cursor = None
    while True:
        params = {"prefix": prefix, "per_page": 1000}
        if delimiter:
            params["delimiter"] = delimiter
        if cursor:
            params["cursor"] = cursor
        d = _check(_s.get(_objects_url(), params=params, timeout=60)).json()
        info = d.get("result_info") or {}
        folders += info.get("delimited") or []
        files += [{"key": o["key"], "size": o.get("size"), "uploaded": o.get("last_modified")}
                  for o in d.get("result") or []]
        cursor = info.get("cursor")
        if not info.get("is_truncated") or not cursor:
            return folders, files


def fetch(key: str, out: Path | None = None, refresh: bool = False) -> Path:
    """Download one object (cached) and return its local path."""
    out = Path(out) if out else CACHE / key
    if out.exists() and not refresh:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _check(_s.get(_objects_url(key), timeout=300))
    tmp = out.with_suffix(out.suffix + ".part")
    tmp.write_bytes(r.content)
    tmp.replace(out)
    return out


def read_parquet(key: str, **kw):
    import pandas as pd
    return pd.read_parquet(fetch(key), **kw)


_DAY = re.compile(r"(\d{4}-\d{2}-\d{2})")


def sync(prefix: str, since: str | None = None, workers: int = 8) -> list[Path]:
    _, files = ls(prefix, delimiter=None)
    keys = [f["key"] for f in files]
    if since:
        keys = [k for k in keys if not _DAY.search(k) or _DAY.search(k).group(1) >= since]
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(fetch, keys))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ls"); p.add_argument("prefix", nargs="?", default="")
    p = sub.add_parser("get"); p.add_argument("key"); p.add_argument("-o", "--out")
    p = sub.add_parser("sync"); p.add_argument("prefix"); p.add_argument("--since")
    a = ap.parse_args()
    if a.cmd == "ls":
        folders, files = ls(a.prefix)
        for f in folders:
            print(f)
        for f in files:
            print(f"{f['key']}\t{f['size']}\t{f['uploaded']}")
    elif a.cmd == "get":
        print(fetch(a.key, Path(a.out) if a.out else None, refresh=True))
    else:
        paths = sync(a.prefix, a.since)
        print(f"{len(paths)} files under {CACHE / a.prefix}")


if __name__ == "__main__":
    sys.exit(main())

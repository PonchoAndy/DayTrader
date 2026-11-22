# 0016. Claude sessions read the R2 storage directly, read-only

- **Status:** Accepted
- **Date:** 2026-11-22
- **Issue:** PonchoAndy/DayTrader#113 (related: #115, #19)

## Context

The collector stores every listing summary, every item, every hour, for US and Europe in Cloudflare R2
(ADR 0005). Until now Claude sessions and the agents couldn't read it: the collector's S3-style keys live
only in GitHub Actions secrets. Agents worked from small exports committed to branches instead:
`tools/market/market.json` (about 430 crafting materials, refreshed by hand, last run 11-20) and
`tools/analyst/pulse.json` (19 watchlist items plus whole-market totals). On 2026-11-22 the Analyst's
market report could rank only crafting materials. Those are about 30% of what sells; gear, ammunition and
consumables were invisible. The owner asked for the analyst "to be able to see everything".

The cloud environment's network proxy can attach a bearer token to requests for a host, but it can't
sign S3 requests (their signature depends on the secret key). So the R2 S3 endpoint can't be used this way.

## Decision

- The owner created a Cloudflare API token with one permission, **Workers R2 Storage: Read**. It's saved
  as a **network secret for `api.cloudflare.com`** on the DayTrader cloud environment. The proxy adds it to
  requests, so no session, agent or file ever holds the value.
- Sessions read the bucket through Cloudflare's REST API for R2 (list objects, get object) with
  **`tools/r2read.py`**: `ls`, `get`, `sync` (with a local cache), and `read_parquet()` for Python.
- The Analyst uses R2 as its main source. The branch exports stay as a fallback and for pages that need a
  small committed file.
- The token can't write or delete. The collector keeps its own keys in GitHub Actions secrets, unchanged.

## Consequences

- The analyst (and any session in this environment) sees every item, hour and house: hourly prices,
  daily and hourly flows, raw pulls (while kept), run logs, both regions, as fresh as the last run.
- Daily flows files are large (~70 MB, ~3 million rows a day), so reads should pick columns and cache
  downloads (the helper caches under `/tmp/r2cache`).
- It only works in sessions on the DayTrader environment. Scheduled tasks and the background Deck
  session work only if they run there too.
- Sessions need pandas and pyarrow: `pip install -r requirements.txt` (a setup-script step on
  the environment).
- **#113 and #115** (widen and refresh the market export) matter less now: they're only needed for
  committed pages, not for analysis.
- If the token is revoked or expires, reads fail with a plain message and agents fall back to the
  exports.

## Alternatives considered

- **Widen the market export** (#113 option a/b) and refresh it daily (#115): no new key, but still a
  slice chosen in advance, size-capped (8 MB) and a day or more old.
- **The collector's S3 keys in the environment:** the proxy can't sign S3 requests, and those keys can
  write and delete.
- **The "Read all resources" preset token:** it works, but it can read the whole Cloudflare account
  (billing, DNS); one permission is enough.

"""Small client for the WoW Forever parts of Blizzard's Game Data API.

Credentials: set BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET (GitHub Actions, local runs).
In Claude's cloud sessions leave them unset: the network proxy adds the key for oauth.battle.net.
"""

from __future__ import annotations

import os
import time

import requests


def get_token(session: requests.Session) -> str:
    cid, secret = os.environ.get("BLIZZARD_CLIENT_ID"), os.environ.get("BLIZZARD_CLIENT_SECRET")
    auth = (cid, secret) if cid and secret else None  # None: the cloud proxy injects the key
    r = session.post("https://oauth.battle.net/token", data={"grant_type": "client_credentials"}, auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def faction_of(house_name: str) -> str:
    for f in ("Alliance", "Horde", "Blackwater"):
        if f.lower() in house_name.lower():
            return f
    return "Unknown"


class Api:
    def __init__(self, region: str = "us"):
        self.region = region
        self.s = requests.Session()
        self.base = f"https://{region}.api.blizzard.com"
        self.dynamic = f"dynamic-forever-{region}"
        self.static = f"static-forever-{region}"
        self.s.headers["Authorization"] = f"Bearer {get_token(self.s)}"

    def get(self, path: str, namespace: str | None = None, retries: int = 4) -> requests.Response:
        """GET with retries on rate limits and server errors. Returns the last response."""
        for attempt in range(retries):
            try:
                r = self.s.get(self.base + path, params={"locale": "en_US"},
                               headers={"Battlenet-Namespace": namespace or self.dynamic}, timeout=120)
            except requests.RequestException:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            return r
        return r

    def houses(self, ruleset: int) -> list[dict]:
        r = self.get(f"/data/wow/ruleset/{ruleset}/auctions/")  # trailing slash required
        r.raise_for_status()
        return sorted(r.json().get("auctions", []), key=lambda h: h["id"])

    def house_listings(self, ruleset: int, house_id: int, kind: str) -> requests.Response:
        """kind: 'auctions' or 'commodities'."""
        suffix = "/commodities" if kind == "commodities" else ""
        return self.get(f"/data/wow/ruleset/{ruleset}/auctions/{house_id}{suffix}")

"""Hourly step for the Stockpile Ticker's scheduled Claude session (#99). Deterministic, so the session only
has to copy files into the page's database and, when this says so, ask the Analyst for briefings.

Reads the export collector/ticker.py commits to branch analyst-data, and the page's `ticker/state` doc
(saved to a file by the session; absent on the first run). Writes:
  <out>/data.json      the `ticker/data` doc: the last --days days of hours and flow days, plus positions
  <out>/brief.json     what the Analyst needs: the last 48 hours in a table, the last 7 flow days, positions,
                       and the moves since the last briefing (only when one is due)
and prints one JSON line: {newest_hour, new_data, briefing_due, reasons, prices}.

A briefing is due when there is none yet, when a 6-hour slot (00, 06, 12, 18 UTC) began since the last one,
(and at least 3 hours after the last one), or on a big move since the last one: a held item's lowest price changed by --move (30%) or more. (Hourly
prices on our houses swing a median ~23% over 12 hours, so a smaller threshold would fire most hours; and
Pristine Hide sits within a copper of its buy price, so "crossed the buy price" would fire constantly.)

Usage: python tools/stockpile-ticker/update.py --ticker ticker.json [--state state.json] --out DIR [--now ISO]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SLOT_HOURS = 6


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def last_value(xs: list):
    return next((v for v in reversed(xs) if v is not None), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--state")
    ap.add_argument("--out", required=True)
    ap.add_argument("--now")
    ap.add_argument("--days", type=int, default=14, help="days of hours kept on the page")
    ap.add_argument("--move", type=float, default=0.30, help="lowest-price change that counts as a big move")
    a = ap.parse_args()
    now = ts(a.now) if a.now else datetime.now(timezone.utc)
    t = json.loads(Path(a.ticker).read_text())
    state = {}
    if a.state and Path(a.state).exists():
        state = json.loads(Path(a.state).read_text())
        state = state.get("data", state)   # an ArtifactData read wraps the doc in {id, data, version}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    hours = t["hours"]
    cut = (ts(hours[-1]) - timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%MZ")
    k = next(i for i, h in enumerate(hours) if h >= cut)
    fd = t["flow_days"][-a.days:]
    nf = len(fd)
    data = {"generatedAt": t["generated_at"], "newestHour": hours[-1], "region": t["region"], "house": t["house"], "boughtAt": t.get("bought_at"),
            "positions": t["positions"], "hours": hours[k:],
            "items": {i: {f: v[k:] for f, v in s.items()} for i, s in t["items"].items()},
            "flow_days": fd, "flows": {i: {f: (v[-nf:] if nf else []) for f, v in s.items()} for i, s in t["flows"].items()}}
    (out / "data.json").write_text(json.dumps(data, separators=(",", ":")))

    prices = {str(p["id"]): last_value(t["items"][str(p["id"])]["min"]) for p in t["positions"]}
    reasons = []
    last = state.get("lastBriefingAt")
    if not last:
        reasons.append("no briefing yet")
    else:
        slot = now.replace(minute=0, second=0, microsecond=0)
        slot -= timedelta(hours=slot.hour % SLOT_HOURS)
        if ts(last) < slot and now - ts(last) >= timedelta(hours=3):   # not right after an extra one
            reasons.append(f"6-hour slot {slot:%H:%M} UTC")
        was = state.get("pricesAtBriefing", {})
        for p in t["positions"]:
            i = str(p["id"])
            a0, a1 = was.get(i), prices.get(i)
            if not a0 or not a1:
                continue
            ch = a1 / a0 - 1
            if abs(ch) >= a.move:
                reasons.append(f"{p['name']} lowest price {ch:+.0%} since the last briefing ({a0} -> {a1} copper)")

    if reasons:
        n48 = next(i for i, h in enumerate(hours) if h >= (ts(hours[-1]) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%MZ"))
        rows = [{"hour_utc": h, **{f"{p['sym']}_{f}": t["items"][str(p["id"])][f][n48 + j] for p in t["positions"]
                                   for f in ("min", "median", "qty")}} for j, h in enumerate(hours[n48:])]
        brief = {"now": now.strftime("%Y-%m-%dT%H:%MZ"), "reasons": reasons, "positions": t["positions"],
                 "prices_at_last_briefing": state.get("pricesAtBriefing"), "last_briefing_at": last,
                 "last_48_hours": rows,
                 "flows_last_7_days": {"days": t["flow_days"][-7:],
                                       **{p["sym"]: {f: t["flows"][str(p["id"])][f][-7:] for f in ("sold", "posted")}
                                          for p in t["positions"]}}}
        (out / "brief.json").write_text(json.dumps(brief, indent=1))
    print(json.dumps({"newest_hour": hours[-1], "new_data": hours[-1] != state.get("lastHour"),
                      "briefing_due": bool(reasons), "reasons": reasons, "prices": prices}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

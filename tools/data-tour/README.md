# Auction Data Tour

A one-off explainer page (claude.ai artifact https://claude.ai/artifact/6wreTZDzn3UnHySAhPz4Td):
what the collected data literally looks like (the four tables) and ways to slice it (by category,
house, time, depth, item version). Feeds the dashboard design in #11.

`data-tour.html` is the published page with its data embedded (`const D = {...}`), computed from four
local snapshots (2026-11-13 23:17 to 2026-11-14 03:17 UTC) with `collector/collect.py`'s
`listing_rows` / `summarize`. Market size = quantity × median price, capped at 3× the item's
typical (median p25) price across houses, because of joke listings like a 9,999,999 g fish.
To update it, rebuild the data from fresh snapshots and republish with the Artifact tool.

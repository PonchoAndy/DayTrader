# Stockpile Ledger (prototype)

Private claude.ai page where the owner logs every buy, sale and vendor trip for the low-level materials stockpile
(`docs/designs/2026-11-15-*`): https://claude.ai/artifact/7R9N1Pc25TM22rWGTG8pAm

- Source: `stockpile-ledger.html` (publish it from this path to update the same page).
- Data lives in the page's artifact database (ArtifactData tool, same URL), not in this repo:
  - `entries/<auto id>`: `{at, action: "buy"|"sell"|"vendor", item, item_id, qty, total (copper), house, note, createdAt}`.
    Written by the owner from the page. Claude reads them; it never edits them unless the owner asks.
  - `prices/current`: `{house, region, asOf, items: {<item_id>: {name, vendor, min}}}`, prices in copper. Written by Claude
    (a live pull of the house's commodities plus vendor sell prices). Refresh it when you review positions.
- Money is shown as gold with 4 decimals (1.0101 = 1g 1s 1c), the owner's format; stored as integer copper.
- Positions use average cost; market value = lowest listing × 0.95 (AH cut) × units held.
- It's the Strategist's "position ledger" (P6) in its simplest form; the app version is #78.

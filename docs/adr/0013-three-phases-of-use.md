# 0013. Three phases of use: playground, app, AH terminal

- **Status:** Accepted (owner, 2026-11-15, in chat)
- **Date:** 2026-11-15
- **Issue:** PonchoAndy/DayTrader#79 (scope), #78 (profile), #88 (ticker)

## Context

By 2026-11-15 DayTrader had hourly data for US and Europe, six helper agents, and a first real stockpile
bought with them. Ideas were arriving faster than they could be placed: a live ticker, an addon to read
bags and purchases, an all-characters profile. We needed to say which belong to now and which to later,
and where each kind of work should happen.

## Decision

DayTrader is used in three phases:

1. **Playground (now).** Claude chat sessions with our data and agents. We use it for real trading
   decisions ("strike while the iron is hot") and to shape how the product should work. Prototype
   pages (Issue Deck, Stockpile Ledger) are fine; polish isn't the goal.
2. **The app (next).** It runs on its own, outside Claude chat sessions: a polished "data center" for
   prices, trends, positions and the economy ("economic intelligence center", PLANNING). Here we decide
   which parts run as agents and which as plain code.
3. **The AH terminal (later).** An in-game addon plus a matching section of the app, used while standing
   at the auction house to actually trade. The addon also feeds the app with what only the game knows:
   the player's characters, bags, bank and purchases (#78).

When an idea comes up, tag it with its phase. Phase-2 and phase-3 features (the live ticker #88,
automatic profile import) are recorded, not built, during phase 1, unless the owner asks.

## Consequences

- The scope check (#79) asks first "which phase is this?", then "what can the player do now?".
- Playground work should leave behind what phase 2 needs: decisions (ADRs), data contracts
  (e.g. ADR 0011 money, ADR 0012 houses), the agents' reports, and lessons about what's worth showing.
- The addon stays read-only and advisory: DayTrader never automates in-game actions (PLANNING, top).

## Alternatives considered

- **Go straight to building the app:** we'd build before learning which signals matter; the playground
  is cheaper for finding out.
- **Stay in chat sessions for good:** they depend on Claude usage limits (hit on 2026-11-15) and can't
  run continuously or serve other players.

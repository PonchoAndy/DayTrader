# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-11-13

## Context

DayTrader is being planned across many chat sessions. Without a written record, the reasons
behind a choice get lost between sessions and decisions get re-argued.

## Decision

Keep Architecture Decision Records in `docs/adr/`, one numbered file per decision, using
`template.md`. Claude writes a record whenever a decision is made in an issue or in chat, and
links the issue.

## Consequences

- The "why" behind the design stays findable, for you and for future Claude sessions.
- Small overhead per decision. Only architecture-level choices get a record, not every detail.
- `docs/PLANNING.md` stays the working notebook; ADRs are the settled outcomes.

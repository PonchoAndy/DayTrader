# 0010. Build-helper agents live in the repo, hand off through saved documents

- **Status:** Accepted (owner, 2026-11-14/15, across the agent sessions; recorded in the 2026-11-15 house cleaning)
- **Date:** 2026-11-15
- **Issue:** PonchoAndy/DayTrader#14, #15

## Context

Claude Code can hand a task to a specialised agent: a short file with a role, the tools it may use
and its standards. The owner wanted to learn to build agents well, using DayTrader's own work. The
first planning (#14) listed six helpers. Building them (sessions of 2026-11-14 and 15) showed what
works:
- An agent only knows its file and its brief. Facts must come from the repo, not be copied in.
- Agents don't talk to each other.
- A new agent file can only be used from the next message.
- In cloud sessions, the GitHub tools have to be loaded on demand.

## Decision

- **Where:** each agent is a file in `.claude/agents/<name>.md`, committed to the repo, so every
  session and scheduled task can use it.
- **Context in three layers:**
  - the agent file: role, standards, where truth lives;
  - the brief: this job;
  - the repo: facts.
  Agent files point to facts and never copy them.
- **Hand-offs are saved documents**, not conversations. Agents write their reports, and the main
  session saves them in `docs/designs/` (mock-ups in `docs/mockups/`), where the owner can read and
  edit them, and later agents read them.
- **Least access:**
  - Most agents are read-only, with GitHub read tools.
  - The Designer writes only mock-ups.
  - The Data engineer edits code and runs it locally.
  - No agent commits, pushes, merges, posts on GitHub or changes settings. The main session does
    that, and the owner merges.
- **Reports in two parts:** first plain words for the owner (with questions as options plus a
  suggested default), then detail for the builder. Agents' questions to the owner become
  `Decide:` issues labelled `agent` (CLAUDE.md).
- **Test every new agent on a real job with a known answer**, with a general agent given the same brief
  as a control where it helps, and check its report against the repo. When an agent gets something
  wrong, fix the layer that caused it (file, brief or docs), not just the output.
- **The roster:**
  - Built: Architect, Strategist, Designer, Researcher, Data engineer.
  - Next: Reviewer, Scribe, Analyst.
  - Later: Economist (#66). *(Built 2026-11-15, owner request: `.claude/agents/economist.md`.)*
  - Advisor agents for players come later, inside the app (#14).

## Consequences

- Agents run inside sessions and use the owner's Claude plan, with no separate cost; each job costs
  minutes of session time (the Researcher's first job took ~8 minutes, its control ~4).
- Every change an agent makes still goes through the main session and the owner's merge.
- Agent files need upkeep when the project's rules change (e.g. new gotchas go into the Data
  engineer's rules).

## Alternatives considered

- **One general assistant for everything:** simpler, but it re-learns the project's rules every time and
  is hard to test. The Researcher-versus-control test showed the agent file adds calibration (trust
  labels, version tagging, checking existing docs).
- **Agents that talk to each other directly:** not supported, and it would hide the reasoning from the owner.
- **Agents that commit and merge themselves:** faster, but removes the owner's check. The Reviewer will
  add a second check before the Merge Now line instead.

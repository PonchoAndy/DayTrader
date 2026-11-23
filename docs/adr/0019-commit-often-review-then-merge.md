# 0019. Commit often, review every batch, then merge

- **Status:** Accepted
- **Date:** 2026-11-22
- **Issue:** none (owner's request in chat, 2026-11-22)

## Context

Since 2026-11-15 the rule was "merge often": whenever a coherent piece of work was pushed, Claude offered a
**Merge Now** line and the Deck showed a Merge Now button. That kept `main` current for new sessions and
scheduled jobs. Nothing checked a batch before it reached `main`, though. On 2026-11-22 alone, seven pull
requests merged, some of them changing the hourly collector and the sales calculations.

The owner asked to change the order: commit more, then merge somewhat more than before, but only after
reviewing what was committed.

## Decision

- **Commit:** Claude commits and pushes every coherent step to its work branch right away. After each push it
  refreshes the Issue Deck's "Unmerged work" panel (`meta/pending`, from `tools/issue-deck/history.py --pending`).
- **Review:** when a meaningful batch has built up, when the owner asks, or when the Deck's **Review** button is
  pressed, Claude reviews the whole branch against `main` with the `code-review` skill (effort medium). It fixes
  what the review finds and records the result in `meta/review` (`clear` or `findings`, with the head it checked).
- **Merge:** the Merge Now line in chat and the Deck's **Merge** button appear only after a clear review of the
  exact head on the branch. Any new commit means reviewing again.
- `CLAUDE.md`, `docs/WORKFLOW.md` and `tools/issue-deck/README.md` describe the steps.

## Consequences

- Each merge carries a review, so collector and calculation changes get a second look before scheduled jobs run
  them.
- Merges are batched rather than one per step, so `main` lags the branch a little longer. The Deck's panel shows
  what's waiting, so nothing gets lost.
- A review adds time and some usage before each merge. Medium effort keeps it proportionate; the owner can ask for
  more on risky batches.
- The Reviewer agent (#20) is still unbuilt. If it's built, it can replace the `code-review` skill in step 2.

## Alternatives considered

- **Keep merging after every step** (the 2026-11-15 rule): fast, but nothing is reviewed.
- **Review only when the owner asks:** cheaper, but the owner isn't deeply technical and wouldn't know when a
  batch is risky.
- **A pull request per batch left open for the owner to approve on GitHub:** puts the reading on the owner.

# Issue Deck

Source of the private claude.ai page where issues are shown as swipeable cards:
https://claude.ai/artifact/RpKHZGqfrwCjAqB9tDBDvL

- `issue-deck.html` is the published page. To change it, edit this file and republish it with
  the Artifact tool, passing the URL above as `url` (otherwise a new, separate page is created).
  Keep the declared capabilities when republishing: `db` with rules
  `issues`, `meta`, `replies`, `briefings` — each `read: "admin", write: "admin"` (owner only) — and
  `mcp` with `{server: "Claude Code Remote", tools: ["fire_trigger", "send_message"]}`.
- The page has no GitHub access. Its data lives in the artifact database:
  - `issues/i<N>`: `{number, title, body, state, updated_at, comments: [{user, created_at, body}], syncedAt}`
  - `briefings/b<N>`: `{number, summary, why, terms: [{term, meaning}], yourPart, basedOn, writtenAt}`.
    Plain-language explainer shown in a card under each issue, written by Claude during syncs
    (`CLAUDE.md` step 3). The page flags it as out of date when the issue's `updated_at` > `basedOn`.
  - `meta/sync`: `{syncedAt}`
  - `meta/syncRequest`: `{state: "running" | "done" | "failed", via: "session" | "background", requestedAt, finishedAt?, error?}`
  - `meta/activeSession`: `{sessionId, kind: "work", triggerId, heartbeatAt}`, written by work sessions
  - `replies/<auto-id>`: `{issue, body, close, reopen, status: "pending" | "posted", createdAt}`
    (empty `body` + `close: true` = "Mark Done" with no comment; `reopen: true` = reopen a
    closed issue). Until synced, the page lets the user undo: "Keep it open" clears `close`,
    "Don't reopen" clears `reopen`, "Delete reply" / "Undo" deletes the doc.
- Sync steps are in the repo's `CLAUDE.md` ("Issue Deck" section).
- **Sending:** Send reply / Mark Done / Reopen save a `replies` doc, then hand it to Claude at once.
  - If `meta/activeSession` was updated in the last 45 minutes (an interactive work session
    writes it), the page fires that session's own task (`triggerId`), which lands in its chat.
    `send_message` is tried next, but the page doesn't appear to be allowed to use it.
  - Otherwise, or if that message fails, the page fires the task "Sync the Issue Deck"
    (`trig_01Qgigo8czoeUjryZZug8zxo`, no schedule). It wakes one long-lived session,
    **"Issue Deck sync (background)"** (`session_015bLnKyEsmDdphwzHN668bv`), which has the repo
    attached and standing sync instructions. (Tasks that start a fresh session each time don't
    get the repo, so they have no GitHub access. That's why the first version failed.)
  - The background session never writes `meta/activeSession`.
  - `meta/route` `{at, route, notes}` records which route the last press took and why.
  - **Refresh** (top) runs the same path to pull changes from GitHub.
  - If the background session is archived or recreated, create a new task with
    `persistent_session_id` pointing at it and update `SYNC_TRIGGER` in the page.
- **Deep links:** `…/artifact/RpKHZGqfrwCjAqB9tDBDvL#i<N>` opens issue N's card, revealing it even if it's closed or filtered out.

## Merge Now

When Claude has work ready to merge into `main`, it sets `meta/mergeReady`
`{ready: true, summary, branch, at}` and the page shows a gold "Ready to merge" bar with a
**Merge Now** button. Pressing it writes `meta/mergeRequest {state: "requested", requestedAt, branch}`
and wakes Claude through the same route as a reply (`dispatch`). Claude opens and merges the pull
request (step 0 of the sync in `CLAUDE.md`), then sets `mergeRequest {state: "done", pr, finishedAt}`
and `mergeReady {ready: false}`; the bar shows "Merged #N" for 15 minutes. A failure shows the
reason (`mergeRequest.error`) and leaves the button available to try again.

## Changes tab (merge history)

A second tab shows every pull request merged into `main` as a vertical timeline, newest first,
grouped by day. Each node shows the time, PR number, title, the areas touched (Agents, Collector,
Docs, Pages, Workflows, Project) and the size; clicking it expands the commits inside it, with their
notes. `#N` references jump to that issue's card. The merge banner links here ("Change history →");
after a merge it opens with that merge expanded. `…#changes` opens the tab directly.

Data: `meta/history` = `{merges: [{pr, title, merged_at, sha, files, added, removed, areas[],
commits: [{sha, at, subject, notes}]}], generatedAt}`, built from git by `history.py` (merge commits
on main's first-parent line) and written by Claude during syncs and after each merge.

# Issue Deck

Source of the private claude.ai page where issues are shown as swipeable cards:
https://claude.ai/artifact/RpKHZGqfrwCjAqB9tDBDvL

- `issue-deck.html` is the published page. To change it, edit this file and republish it with
  the Artifact tool, passing the URL above as `url` (otherwise a new, separate page is created).
  Keep the declared capabilities when republishing: `db` with rules
  `issues`, `meta`, `replies` — each `read: "admin", write: "admin"` (owner only) — and
  `mcp` with `{server: "Claude Code Remote", tools: ["fire_trigger", "send_message"]}`.
- The page has no GitHub access. Its data lives in the artifact database:
  - `issues/i<N>`: `{number, title, body, state, updated_at, comments: [{user, created_at, body}], syncedAt}`
  - `meta/sync`: `{syncedAt}`
  - `meta/syncRequest`: `{state: "running" | "done" | "failed", via: "session" | "background", requestedAt, finishedAt?, error?}`
  - `meta/activeSession`: `{sessionId, kind: "work" | "background", heartbeatAt}`, written by Claude sessions
  - `replies/<auto-id>`: `{issue, body, close, reopen, status: "pending" | "posted", createdAt}`
    (empty `body` + `close: true` = "Mark Done" with no comment; `reopen: true` = reopen a
    closed issue). Until synced, the page lets the user undo: "Keep it open" clears `close`,
    "Don't reopen" clears `reopen`, "Delete reply" / "Undo" deletes the doc.
- Sync steps are in the repo's `CLAUDE.md` ("Issue Deck" section).
- **Sending:** Send reply / Mark Done / Reopen save a `replies` doc, then hand it to Claude at once.
  If `meta/activeSession` was updated in the last 45 minutes, the page sends that session an
  `[Issue Deck] …` message (lands in its chat). Otherwise it fires the on-demand task
  "Sync the Issue Deck" (`trig_014NWfEMMZzor2Ws7wNZDxkP`, no schedule), which starts a small
  background session that registers itself in `meta/activeSession`, so follow-up replies go to it.
  Syncs re-check for pending replies before finishing. If `send_message` isn't available or
  fails, the page falls back to the task. **Refresh** (top) runs the same path to pull changes.
  If the task is deleted or recreated, update `SYNC_TRIGGER` in the page; keep the task's
  self-contained prompt in step with `CLAUDE.md` when the sync steps change.

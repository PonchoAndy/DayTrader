# Issue Deck

Source of the private claude.ai page where issues are shown as swipeable cards:
https://claude.ai/artifact/RpKHZGqfrwCjAqB9tDBDvL

- `issue-deck.html` is the published page. To change it, edit this file and republish it with
  the Artifact tool, passing the URL above as `url` (otherwise a new, separate page is created).
  Keep the declared capabilities when republishing: `db` with rules
  `issues`, `meta`, `replies` — each `read: "admin", write: "admin"` (owner only) — and
  `mcp` with `{server: "Claude Code Remote", tools: ["fire_trigger"]}`.
- The page has no GitHub access. Its data lives in the artifact database:
  - `issues/i<N>`: `{number, title, body, state, updated_at, comments: [{user, created_at, body}], syncedAt}`
  - `meta/sync`: `{syncedAt}`
  - `meta/syncRequest`: `{state: "running" | "done" | "failed", requestedAt, finishedAt?, error?}`
  - `replies/<auto-id>`: `{issue, body, close, reopen, status: "pending" | "posted", createdAt}`
    (empty `body` + `close: true` = "Mark Done" with no comment; `reopen: true` = reopen a
    closed issue). Until synced, the page lets the user undo: "Keep it open" clears `close`,
    "Don't reopen" clears `reopen`, "Delete reply" / "Undo" deletes the doc.
- Sync steps are in the repo's `CLAUDE.md` ("Issue Deck" section).
- **Sync now button:** fires the on-demand Claude task "Sync the Issue Deck"
  (`trig_014NWfEMMZzor2Ws7wNZDxkP`, no schedule) through the Claude Code Remote connector. Each
  press starts a fresh cloud session that runs the sync and writes `meta/syncRequest` when done.
  If that task is deleted or recreated, update `SYNC_TRIGGER` in the page. The task's prompt is
  self-contained; keep it in step with `CLAUDE.md` if the sync steps change.
- Local preview: the page needs `window.claude.use("db")`; mock it and serve marked/DOMPurify
  locally (the CDN may be blocked in cloud sessions).

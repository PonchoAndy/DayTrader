# DayTrader — notes for Claude

Tool to collect, analyze and display WoW Forever auction house data. Planning stage.

- Background and findings: `docs/PLANNING.md`. Workflow: `docs/WORKFLOW.md`.
- Work is tracked in GitHub issues on `PonchoAndy/DayTrader`. At the start of a task, read
  the relevant issue; if the user asks "what's next?", list open issues and suggest the first
  unblocked one.
- Reference the issue in commit messages (`Refs #N`); in PR descriptions use `Closes #N`.
- Record research results and decisions in `docs/PLANNING.md`, and comment on the issue.
- The user is not deeply technical: explain steps plainly and say where to click.
- Never commit secrets. Keys live in GitHub Actions secrets or the cloud environment's
  network secrets, never in files.

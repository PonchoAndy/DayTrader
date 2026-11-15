# How we work

All work is tracked as **GitHub issues**: https://github.com/PonchoAndy/DayTrader/issues

## Issue types (title prefix)

| Prefix | Meaning |
|---|---|
| `Tracking:` | Groups related issues as sub-issues. Closes when all of them are done. |
| `Decide:` | A choice only you can make. Answer in a comment, then close it. Claude records the outcome as an ADR in `docs/adr/`. |
| `Setup:` | An account, credential or service to set up. |
| `Build:` | Code to write. Usually Claude. |
| `Research:` | Something to find out. Results go into `docs/PLANNING.md`. |
| `Idea:` | A product idea for later, under the roadmap tracker (#46). Not decided or scheduled. |

Each issue says **Who** does it, what it's **Blocked by**, and when it's **Done**.

## The loop

1. **Pick an issue.** Start a Claude session with "work on #9" (or ask "what's next?").
2. **Claude works on a branch**, and commit messages mention the issue (`Refs #9`).
3. **Merge often.** Whenever a coherent piece of work is done (an agent, a design, a fix, a
   decision recorded), Claude ends its reply with a **Merge Now** line. Reply "merge" and Claude
   opens a pull request and merges it. `Closes #9` in the description closes finished issues.
4. **Why often:** work on a branch is already saved on GitHub, but only `main` counts. Scheduled
   jobs run from `main`, and new Claude sessions start from `main`, so anything unmerged is
   invisible to them. Questions and decisions still go in issue comments, so they stay with the work.

## Rules

- Never paste a secret into an issue, comment, commit, chat or file in the repo.
- New ideas or problems → open a new issue rather than growing an old one.
- Keep each issue small enough to finish in one sitting.

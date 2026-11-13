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

Each issue says **Who** does it, what it's **Blocked by**, and when it's **Done**.

## The loop

1. **Pick an issue.** Start a Claude session with "work on #9" (or ask "what's next?").
2. **Claude works on a branch**, and commit messages mention the issue (`Refs #9`).
3. **Claude opens a pull request** with `Closes #9` in the description, when you ask for one.
   Merging the PR closes the issue automatically.
4. **You review and merge.** Questions and decisions go in issue comments, so they stay
   with the work.

## Rules

- Never paste a secret into an issue, comment, commit, chat or file in the repo.
- New ideas or problems → open a new issue rather than growing an old one.
- Keep each issue small enough to finish in one sitting.

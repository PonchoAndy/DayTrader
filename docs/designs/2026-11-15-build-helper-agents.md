# Build-helper agents: Researcher, Data engineer, Reviewer (outlines)

2026-11-15. Fuller outlines for #17, #18 and #20, moved up to be the next three agents built (#15).
Each outline is what the agent file (`.claude/agents/<name>.md`) will say, plus how we'll test it.
The three existing agents set the pattern: a short file with the role, standards and where truth
lives; a brief per job; facts read from the repo, never copied in.

## Where they fit

```
Researcher ──► Strategist ──► Architect ──► Designer
 (what's true)  (what's needed) (how to build) (how to show)
                                     │
                                     ▼
                              Data engineer ──► Reviewer ──► you press Merge
                               (builds it)      (checks it)
```

- The **Researcher** feeds facts to everyone. Until now the main session did research by hand
  (TSM formulas, Forever auction house rules).
- The **Data engineer** builds what the Architect designs. Until now the main session did all the
  building (collector, Europe, flows).
- The **Reviewer** checks every change before the **Merge Now** line goes out, so "merge often"
  doesn't mean "merge unchecked".

Why these three now: we merge several times a session, the collector is real and runs every hour,
and research questions keep coming up mid-session. A mistake in the collector costs hours of data
that can't be recovered; that's the case for a builder that knows the gotchas and a checker who
looks before merging.

---

## 1. Researcher (#17)

**Job.** Find out what's true about WoW Forever and its trading: game rules (cuts, deposits,
durations, which cities share listings), the Blizzard API, how tools like TSM work, what
experienced traders do. Answer `Research:` issues and questions the other agents raise.

**Who asks it:** the main session, usually because the Strategist, Architect or owner hit an
unknown ("do undercuts post right away?", "what's the cut at a neutral house?").

**Tools:** Read, Grep, Glob, WebSearch, WebFetch, **Bash (for `curl` only)**, ToolSearch, GitHub
read tools. Bash is there because this session showed WebFetch sometimes can't reach newly allowed
sites while `curl` through the proxy can. It doesn't write files; it returns a report and the main
session records it in `docs/PLANNING.md` and on the issue (as CLAUDE.md requires).

**Standards it holds to**
- **Which game is this source about?** The biggest trap: retail WoW, Classic, Classic Era and
  Forever have different auction house rules (retail's commodities are region-wide, for example).
  Every source gets tagged with the version it covers; a retail fact is not a Forever fact.
- **How much to trust it,** on a fixed ladder:
  1. Blizzard official (API docs, patch notes, blue posts)
  2. Our own data (something we can see in the collected pulls)
  3. Owner's in-game check (#13)
  4. Datamined game files (wago.tools)
  5. Community-tested (TSM support, the WoW wiki)
  6. Guides and forum posts
  7. Unsourced or SEO pages: mention only, never rely on
- **Dated:** when the source was written, and whether a patch since could have changed it
  (the Nov 17 maintenance changes the minimum deposit, for example).
- **Blocked site?** Name the host to allow; don't guess what the page says.

**What it returns**
- **Part 1 (owner):** the answer in a sentence; confidence (firm / likely / unknown); what
  would settle it.
- **Part 2 (main session):**
  - a sources table (link, game version, date, trust level, what it says);
  - conflicts with PLANNING or accepted ADRs;
  - **next steps sorted by who can settle them:**
    - in-game checks → owner (added to #13 or a new card);
    - claims our data could test → hypotheses for the Analyst, written before anyone looks;
    - decisions → `Decide:` cards with the `agent` label.

**Won't:** treat a guide as fact, edit code, decide anything.

**First job (test):** the auction house cut and deposit in Forever: the 5% / 15% cut is still
unconfirmed, and the Nov 17 maintenance changes the minimum deposit. It's time-sensitive and has a
known partial answer in PLANNING, so we can check its work. **Control:** compare against a
general agent given the same brief.

---

## 2. Data engineer (#18)

**Job.** Build and keep running the data pipeline:
- the hourly collector (`collector/collect.py`), listing flows (`collector/flows.py`) and the
  daily roll-up still to come (#26);
- the GitHub Actions workflow;
- storage layout in R2;
- data-quality checks.

It builds from the Architect's designs and ADRs; it doesn't redesign.

**Tools:** Read, Grep, Glob, **Edit, Write, Bash** (run Python, run the collector with `--local`,
call the Blizzard API with the session's saved key), ToolSearch, GitHub read tools plus the Actions
read tools (list runs, read job logs). It's the first agent that writes code.
- It **edits files and tests locally**.
- The main session commits, pushes and offers Merge Now, after the Reviewer has looked.
- It never merges or touches secrets.

**Standards it holds to** (the gotchas we learned the hard way):
- **Regions never mix:** every stored path goes through `prefix(region)`. House IDs repeat across
  regions (ADR 0009).
- **The hourly run stays under 60 seconds**, because GitHub bills whole minutes. Every change to
  the hourly job reports the measured `job_seconds` before and after.
- **Data that expires is urgent:** raw pulls disappear after 14 days (from ~Nov 28). Anything
  that needs raw data is built and backfilled before then.
- **Don't break readers:**
  - add columns, never rename or drop them silently;
  - when a file's shape changes, update every reader (`report.py`, `flows.py`, demo pages) in the
    same change.
- **Jobs catch up:** a missed run fixes itself next time (as flows does), and re-running is
  harmless.
- **The session can't read R2:**
  - test with `--local` and live API pulls;
  - get data out through a workflow job that commits it (the `demo` switch).
- **Costs:** every change that adds minutes or storage updates `docs/SYSTEMS.md`.
- Never hard-code faction, ruleset or region (ADR 0003); never commit keys or data files.

**Data-quality checks it owns:**
- missing hours (#54);
- a house that comes back empty;
- the API changing shape;
- Blizzard's refresh minute drifting;
- Europe skipped for being late;
- items with no name.

**What it returns**
- **Part 1 (owner):** what changed and what you'd notice; cost and time impact; anything you
  need to do (click-by-click).
- **Part 2 (main session and Reviewer):**
  - files changed;
  - how it was tested, with real numbers (rows, seconds, sizes);
  - docs updated;
  - risks and follow-ups.

**Won't:** change a design without saying so (it flags it for the Architect), widen network
access, edit workflows' secrets.

**First job (test):** an hourly **health check**: after each run, flag missing hours, empty houses
and late Europe pulls in the run log, and a small "health" section in the report. It's small,
useful today (it settles #54), and touches the hourly job, so it tests the 60-second rule.

---

## 3. Reviewer (#20)

**Job.** Check a change before it's merged and tell the owner, plainly, whether it's safe to
merge. It runs when the main session is about to send the **Merge Now** line (and on any PR the
owner names).

**Tools:** Read, Grep, Glob, **Bash** (for `git diff`, `git log` and running tests or a
`--local` collector run only), ToolSearch, GitHub read tools including pull request reads. No
Edit or Write: a reviewer that fixes things stops being a second pair of eyes. It returns findings;
the main session fixes them or explains why not.

**What it checks, most important first**
1. **Blockers:** anything that loses data, leaks a secret, or costs money:
   - keys or data files in the diff;
   - region-less paths;
   - an hourly job that could pass 60 s;
   - a workflow schedule or condition that silently stops a job (scheduled runs only start from
     `main`);
   - deleting or overwriting stored files;
   - lifecycle rules that don't match new folders.
2. **Correctness:** bugs, edge cases (missed hours, first run with no history, empty houses,
   Europe late), readers that the change breaks.
3. **Against the plan:** the issue's "Done when", accepted ADRs, the Architect's design if
   there is one.
4. **Docs in step:** SYSTEMS, `collector/README.md` and PLANNING figures still true (we've
   shipped stale ":27" references before).
5. **Clarity:** code someone else could follow. Nits last, and few.

Claude Code already has general review commands (`/code-review`, `/security-review`). The
Reviewer adds what they can't know: this project's ADRs, gotchas and the cost of a lost hour.
We can run both.

**What it returns**
- **Verdict for the owner** (one line): *Safe to merge*, *Merge after fixes*, or *Don't merge*,
  plus why.
- **Findings,** ranked as Blocker / Should fix / Nit. Each finding gives:
  - the file and line;
  - what goes wrong, as a concrete scenario ("if Europe is late and…");
  - a suggested fix.
- **What it couldn't check** (for example, real R2 data).

**Won't:** rewrite the change, approve or merge, or post on GitHub by itself. The main session
posts a summary on the PR if the owner wants one.

**First job (test): a planted bug.** Review the flows code from before the "listing age" fix
(when every listing looked under 2 hours old) and see if it finds that bug unprompted. A reviewer
is only useful if it catches real mistakes, and we know the answer here. **Control:** run
`/code-review` on the same diff.

---

## Order and what changes in the workflow

1. **Researcher** first. It's the smallest and safest (read-only), and the Nov 17 deposit
   question has a date on it.
2. **Data engineer** next. Its first job settles #54 and readies us for the daily roll-up.
3. **Reviewer** third, tested on the planted bug and then on the Data engineer's first change:
   the two are meant to work as a pair.

Then Scribe (#21) and Analyst (#19). The Analyst needs about a week of flows first.

**Workflow change once the Reviewer exists** (goes into CLAUDE.md): before the Merge Now line, the
main session runs the Reviewer on `git diff main...HEAD` and puts its one-line verdict next to the
Merge Now line. Small doc-only changes skip it.

## Open questions for the owner
- **Reviewer on every merge, or only when code changes?**
  - (a) every merge;
  - **(b) only when code or workflows change** (suggested; doc-only merges stay quick).
- **Researcher saves its own notes?**
  - **(a) No, the main session records them in PLANNING** (suggested; one place for findings);
  - (b) it writes `docs/research/<date>-<topic>.md` itself.

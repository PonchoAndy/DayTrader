"""Build the Issue Deck's change history (the "Changes" tab) from git.

Every pull request merged into main is a merge commit on main's first-parent line. For each one this
collects the PR number and title, when it merged, the size of the change, which areas it touched,
and the commits inside it (subject + notes). Output: JSON for the Deck's `meta/history` doc.

    git fetch origin main
    python tools/issue-deck/history.py > /tmp/history.json

With --pending BRANCH it instead lists the work waiting on BRANCH that isn't on main yet (the Deck's
"Unmerged work" panel, `meta/pending`): head sha, commits, size and areas.

    git fetch origin main <branch>
    python tools/issue-deck/history.py --pending origin/<branch> > /tmp/pending.json
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

if sys.argv[1:2] == ["--pending"] and len(sys.argv) < 3:
    sys.exit("usage: history.py --pending origin/<branch>")
PENDING = sys.argv[2] if sys.argv[1:2] == ["--pending"] else None
REF = "origin/main" if PENDING else (sys.argv[1] if len(sys.argv) > 1 else "origin/main")
SEP, END = "\x1f", "\x1e"
DROP = re.compile(r"^(Co-Authored-By|Claude-Session|Signed-off-by):", re.I)
AREAS = {".claude": "Agents", "collector": "Collector", ".github": "Workflows", "docs": "Docs", "tools": "Pages"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def clean(body: str) -> str:
    return "\n".join(l for l in body.strip().splitlines() if not DROP.match(l.strip())).strip()


def commits(a: str, b: str) -> list[dict]:
    out = git("log", "--no-merges", "--reverse", f"--format=%H{SEP}%cI{SEP}%s{SEP}%b{END}", f"{a}..{b}")
    rows = []
    for rec in filter(str.strip, out.split(END)):
        sha, when, subject, body = (rec.strip("\n").split(SEP) + ["", "", "", ""])[:4]
        rows.append({"sha": sha[:7], "at": when, "subject": subject.strip(), "notes": clean(body)})
    return rows


def stat_counts(a: str, b: str) -> tuple[int, int, int]:
    """(files, insertions, deletions); --shortstat leaves out a part that is zero, so match each by name."""
    stat = git("diff", "--shortstat", a, b)
    n = lambda word: int(m.group(1)) if (m := re.search(rf"(\d+) {word}", stat)) else 0
    return n("file"), n("insertion"), n("deletion")


def size(a: str, b: str) -> dict:
    f, add, rem = stat_counts(a, b)
    files = git("diff", "--name-only", a, b).split()
    return {"files": f, "added": add, "removed": rem,
            "areas": sorted({AREAS.get(f.split("/")[0], "Other") if "/" in f else "Project" for f in files})}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if PENDING:
    base = git("merge-base", REF, PENDING).strip()
    out = {"branch": PENDING.removeprefix("origin/"), "head": git("rev-parse", "--short=7", PENDING).strip(),
           "base": base[:7], "commits": commits(REF, PENDING), **size(base, PENDING), "generatedAt": now()}
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.exit(0)

merges = []
log = git("log", "--first-parent", "--merges", f"--format=%H{SEP}%P{SEP}%cI{SEP}%s{SEP}%b{END}", REF)
for rec in filter(str.strip, log.split(END)):
    sha, parents, when, subject, body = (rec.strip("\n").split(SEP) + [""] * 5)[:5]
    m = re.match(r"Merge pull request #(\d+)", subject)
    p = parents.split()
    if not m or len(p) < 2:
        continue
    nfiles, nadd, nrem = stat_counts(p[0], sha)
    files = git("diff", "--name-only", p[0], sha).split()
    areas = sorted({AREAS.get(f.split("/")[0], "Other") if "/" in f else "Project" for f in files})
    merges.append({
        "pr": int(m.group(1)),
        "title": clean(body).splitlines()[0] if clean(body) else subject,
        "merged_at": when,
        "sha": sha[:7],
        "files": nfiles,
        "added": nadd,
        "removed": nrem,
        "areas": areas,
        "commits": commits(p[0], p[1]),
    })

json.dump({"merges": merges, "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
          sys.stdout, ensure_ascii=False)

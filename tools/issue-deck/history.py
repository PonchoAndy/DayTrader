"""Build the Issue Deck's change history (the "Changes" tab) from git.

Every pull request merged into main is a merge commit on main's first-parent line. For each one this
collects the PR number and title, when it merged, the size of the change, which areas it touched,
and the commits inside it (subject + notes). Output: JSON for the Deck's `meta/history` doc.

    git fetch origin main
    python tools/issue-deck/history.py > /tmp/history.json
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone

REF = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
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


merges = []
log = git("log", "--first-parent", "--merges", f"--format=%H{SEP}%P{SEP}%cI{SEP}%s{SEP}%b{END}", REF)
for rec in filter(str.strip, log.split(END)):
    sha, parents, when, subject, body = (rec.strip("\n").split(SEP) + [""] * 5)[:5]
    m = re.match(r"Merge pull request #(\d+)", subject)
    p = parents.split()
    if not m or len(p) < 2:
        continue
    stat = git("diff", "--shortstat", p[0], sha).strip()
    nums = [int(x) for x in re.findall(r"(\d+) (?:file|insertion|deletion)", stat)]
    files = git("diff", "--name-only", p[0], sha).split()
    areas = sorted({AREAS.get(f.split("/")[0], "Other") if "/" in f else "Project" for f in files})
    merges.append({
        "pr": int(m.group(1)),
        "title": clean(body).splitlines()[0] if clean(body) else subject,
        "merged_at": when,
        "sha": sha[:7],
        "files": nums[0] if nums else 0,
        "added": nums[1] if len(nums) > 1 else 0,
        "removed": nums[2] if len(nums) > 2 else 0,
        "areas": areas,
        "commits": commits(p[0], p[1]),
    })

json.dump({"merges": merges, "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
          sys.stdout, ensure_ascii=False)

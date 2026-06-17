#!/bin/bash
# SessionStart hook — auto-loads workspace memory into the session context.
# Purpose: every new session (including mobile / Claude Code on the web) wakes up
# with fresh, current memory instead of a blank slate.
set -euo pipefail

# Resolve repo root: prefer CLAUDE_PROJECT_DIR, fall back to this script's location.
ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

ROOT="$ROOT" python3 - <<'PY'
import json, os, datetime, glob

root = os.environ["ROOT"]
parts = []

def add(title, relpath):
    p = os.path.join(root, relpath)
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                body = f.read().strip()
        except Exception as e:
            body = f"(could not read: {e})"
        if body:
            parts.append(f"===== {title} ({relpath}) =====\n{body}")

# 1. Identity + who we're helping + curated long-term memory (cheap, current)
add("IDENTITY", "IDENTITY.md")
add("USER", "USER.md")
add("MEMORY (long-term, curated)", "MEMORY.md")

# 2. Recent daily notes for continuity: today + yesterday
today = datetime.date.today()
loaded_daily = False
for d in (today, today - datetime.timedelta(days=1)):
    rel = f"memory/{d.isoformat()}.md"
    if os.path.isfile(os.path.join(root, rel)):
        add(f"DAILY {d.isoformat()}", rel)
        loaded_daily = True

# 3. Fallback: if no today/yesterday note, load the most recent daily so the
#    session still has the last known context instead of nothing.
if not loaded_daily:
    dailies = sorted(glob.glob(os.path.join(root, "memory", "20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")))
    if dailies:
        rel = os.path.relpath(dailies[-1], root)
        add("DAILY (most recent available)", rel)

header = (
    "Workspace memory auto-loaded by the SessionStart hook. "
    "These files are the source of truth for continuity across sessions. "
    f"Loaded on {today.isoformat()}."
)
context = header + "\n\n" + "\n\n".join(parts) if parts else header + "\n\n(no memory files found)"

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context
    }
}))
PY

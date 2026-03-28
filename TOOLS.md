# TOOLS.md — Available Tools & Safety

**Scope:** What's installed, how to use safely

---

## 🛠️ Available Tools

### Python (venv)
```bash
~/.openclaw/workspace/.venv/bin/python
pip: 26.0.1
Playwright: 1.58.0 (Chromium v145, Firefox, WebKit)
```
✅ Use: `source .venv/bin/activate && python script.py`

### Node.js
```bash
Node: 22.22.1
npm: 10.9.4 (global: ~/.npm-global)
```
✅ Use: `npm install <pkg>` (local) or `npm install -g <pkg>` (global)

### System
```bash
Git: 2.43.0
curl: 8.5.0
wget: 1.21.4
gcc/make: 13.3.0 / 4.3
```

### Applications
```bash
Firefox: 148.0.2 (system)
Telegram: 6.6.2 (flatpak)
```
✅ Telegram: `flatpak run org.telegram.desktop`

---

## ⚠️ Safety Rules (ACTIVE)

### Exec Approvals
```
security: allowlist
ask: on-miss (ask for approval if unknown)
timeout: 120 seconds
strictEval: enabled
loopDetection: enabled
```

**Auto-allowed:** file reads, memory ops, web searches (GET)  
**Needs approval:** exec, file writes, network mutations (POST/PUT), installs

### Workspace
```
venv: ~/.openclaw/workspace/.venv (ALWAYS use)
DON'T install globally: pip install ❌
DO install in venv: python -m pip install ✅
```

### External Actions
```
❌ git push (needs approval)
❌ npm install -g (needs approval)
❌ curl -X POST to unknown URLs (needs approval)
✅ git status, git diff (read-only)
✅ python script.py (in venv, if whitelisted)
```

---

## 🚫 Off-Limits

```
❌ ~/.openclaw/openclaw.json (without backup + diff)
❌ ~/.openclaw/exec-approvals.json (without backup + diff)
❌ /etc/shadow, ~/.ssh/ (secrets)
❌ System directories
```

---

## Backups

```
Location: ~/.openclaw/workspace/backups/
  • openclaw.json.bak
  • exec-approvals.json.bak
```

Before any config change → compare with backup.

---

## Safe Patterns

```bash
# Test before execute
python script.py --dry-run

# Show diff before apply
diff backups/openclaw.json.bak ~/.openclaw/openclaw.json

# Use venv always
source .venv/bin/activate

# Request approval for external
git push origin main (needs OK)
```

# HEARTBEAT.md — Regular Checks

**Run:** ~30 minutes  
**When no issues:** reply `HEARTBEAT_OK`

---

## First run after gateway restart / lost context

1. Recover from written evidence first.
2. Reply in 2-4 lines max:
   - active task
   - last proven step
   - next step
3. If recovery is weak, say plainly: `progress unknown`.
4. Do not restart the whole task by default.

---

## Quick check

Run:
```bash
openclaw status | grep -E "Gateway|running"
```

If daemon is not responding, report it. Do not auto-restart.

---

## Reporting

- Use command output as evidence.
- If evidence is mixed or incomplete, say that.
- If nothing needs attention, reply exactly: `HEARTBEAT_OK`

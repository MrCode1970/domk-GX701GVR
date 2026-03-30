# HEARTBEAT.md — Regular Checks

**Run:** ~30 minutes  
**When no issues:** reply `HEARTBEAT_OK`

---

## Purpose

Heartbeat is a **cheap watchdog**, not a recovery or maintenance workflow.
Do the smallest check that can detect a real issue.

---

## Default check

Run:
```bash
openclaw status | grep -E "Gateway|running"
```

If daemon is not responding, report it.
Do not auto-restart.

---

## Recovery policy

- Do **not** run recovery just because the session is new, reset, or compacted.
- Do **not** read memory files during heartbeat unless the check itself proves something is wrong and recovery is required to explain the alert.
- If evidence is incomplete, say so briefly.

---

## Reporting

- Use command output as evidence.
- If nothing needs attention, reply exactly: `HEARTBEAT_OK`
- If something needs attention, reply with a short alert only.

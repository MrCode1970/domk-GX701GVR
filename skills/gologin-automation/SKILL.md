---
name: gologin-automation
description: Operate browser automation with Chromium persistent profiles and Playwright inside OpenClaw. Use when creating reusable browser profiles, preserving logged-in sessions across restarts, launching visible browser windows for supervised work, or controlling a Playwright-launched persistent browser with low token usage. Legacy Gologin exploration may appear in notes, but the active workflow is Chromium persistent profiles + Playwright.
---

# Chromium Persistent Profiles + Playwright

Use this skill to build and operate a browser-automation workspace around Chromium persistent profiles.

## Core workflow

1. Prepare isolated browser-agent workspace files.
2. Define profile registry in `agents/browser-agent/config/profiles.json`.
3. Launch a visible persistent browser profile through Playwright.
4. Log in manually where needed.
5. Reuse the same profile folder on later launches.
6. Control the live browser when it was launched from the Playwright process.
7. Keep token usage low and avoid image-heavy flows by default.

## Rules

- Prefer visible browser mode for shared work.
- Do not use screenshots by default.
- If a browser action is likely to cause high token/image usage, stop and warn first.
- Treat logins, 2FA, payment confirmations, and destructive actions as manual-confirmation steps.
- Prefer session reuse over repeated logins.
- Prefer persistent Chromium profiles over third-party anti-detect tools unless explicitly needed.

## Proven result

Confirmed in this workspace:
- Google login can succeed in a persistent Chromium profile when launched with the hardened Playwright launcher.
- Session persists across restart for the same profile.

## Files

For project-specific notes, read and update:
- `/home/domk/.openclaw/workspace/agents/browser-agent/README.md`
- `/home/domk/.openclaw/workspace/agents/browser-agent/TASKS.md`
- `/home/domk/.openclaw/workspace/agents/browser-agent/WORKLOG.md`
- `/home/domk/.openclaw/workspace/agents/browser-agent/config/profiles.json`
- `/home/domk/.openclaw/workspace/agents/browser-agent/scripts/launch_profile.py`

## References

If needed, add detailed references under `references/` later instead of bloating this file.

# Discord Voice Runbook

## Current MVP config

- Discord text channel remains enabled.
- Discord voice mode is enabled in `~/.openclaw/openclaw.json`.
- Voice `autoJoin` is disabled.
- Voice TTS uses Edge with `ru-RU` locale to avoid extra API key dependencies.

## First live test

1. Make sure the bot can see the target voice channel in Discord.
2. Make sure the bot has `Connect`, `Speak`, and `Use Application Commands`.
3. Join the target voice channel with the allowlisted user account.
4. In Discord, run `/vc join`.
5. Ask a short question in voice.
6. Wait for the spoken reply.
7. Run `/vc status` to confirm the active voice session.

## Local diagnostics

Check service health:

```bash
set -a && source ~/.openclaw/openclaw.env && set +a
openclaw channels status --probe
openclaw doctor
systemctl --user status openclaw-gateway --no-pager
```

Tail gateway logs:

```bash
journalctl --user -u openclaw-gateway -f
```

Or via OpenClaw RPC logs:

```bash
set -a && source ~/.openclaw/openclaw.env && set +a
openclaw logs --plain --follow --token "$OPENCLAW_GATEWAY_TOKEN"
```

## What success looks like

- `/vc join` succeeds without an error reply.
- Gateway logs show Discord is connected and no immediate voice transport errors appear.
- A short spoken question gets a spoken response.
- `/vc status` shows an active voice session.

## Common failure checks

- Slash command missing:
  native commands are not yet visible in the guild; wait for command reconcile or restart the gateway once.
- Bot joins but says nothing:
  check TTS provider errors in gateway logs.
- Bot cannot join:
  verify voice-channel permissions for the bot.
- Repeated decrypt failures:
  leave and rejoin once; if it persists, inspect Discord voice transport logs and channel settings.

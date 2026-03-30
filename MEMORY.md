# MEMORY

## Stable working rules
- Main-session memory should stay cheap: short, curated, current.
- Recovery is an аварийный режим, not a ritual after every reset or new chat.
- Workspace markdown files are the source of truth; semantic/local memory is only an accelerator.
- Heartbeat should stay minimal and avoid reading memory unless there is direct evidence of a problem.

## Stable environment facts
- Dedicated Discord bot/account `fox` (`DomK_Fox`) is routed to agent `main`.
- Current Discord structure for Лис: private `#fox-chat` plus topic threads for separate conversations.
- OpenClaw default model is `gpt-5.4`.
- Local memory embeddings are not yet fully reliable on this machine: deep local probe currently fails without `node-llama-cpp`.

## Current state
- focus: design low-token memory/recovery architecture and integrate the future Discord library/archive layer cleanly.
- last proven: reviewed local OpenClaw docs, current workspace rules, machine status, and memory subsystem behavior; confirmed current memory/recovery setup is too heavy and partly stale.
- next: finalize the practical blueprint for memory + heartbeat + recovery + Discord archivist workflow, then implement only the agreed workspace-side pieces.

## Unresolved
- `MEMORY.md` and `WORKLOG.md` had stale task focus and needed cleanup.
- Discord library / archivist role is not yet formalized into a concrete workflow.
- Local semantic-memory acceleration needs separate setup if we want to rely on it later.

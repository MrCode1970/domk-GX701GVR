# MEMORY

## Stable working rules
- Main-session memory should stay cheap: short, curated, current.
- Recovery is an аварийный режим, not a ritual after every reset or new chat.
- Workspace markdown files are the source of truth; semantic/local memory is only an accelerator.
- Heartbeat should stay minimal and avoid reading memory unless there is direct evidence of a problem.
- **Обновляю файлы сразу после урока, не откладываю** — каждое замечание = вывод + изменение правила
- **Говорю хозяину на лету**, когда вижу что-то значимое, не жду конца сессии
- **Система развития:** не очки, а видимый прогресс в поведении (записано в memory/YYYY-MM-DD.md)

## Stable environment facts
- Dedicated Discord bot/account `fox` (`DomK_Fox`) is routed to agent `main`.
- Current Discord structure for Лис: private `#fox-chat` plus topic threads for separate conversations.
- OpenClaw default model is `gpt-5.4`.
- Local memory embeddings are not yet fully reliable on this machine: deep local probe currently fails without `node-llama-cpp`.

## Current state
- focus: VSC integration ready. First automation (Git Auto-Commit) queued.
- last proven: Фаза 4 завершена. Все системные файлы готовы (vsc-integration.md, .vscode/settings.json, automation-ideas.md). Git коммит 6473aec.
- next: Первая автоматизация (Git Auto-Commit для kb/). Потом weekly reminder и daily archive.

## Stable working rules
- **Workflow:** постановка → решение → результат → архив (Discord → KB → git)
- **Memory modes:** MEMORY.md (ключевые факты), memory/YYYY-MM-DD.md (дневник, 7 дней), kb/ (вечная истина)
- **Git:** автокоммит на изменение kb/, история в git log
- **Discord:** обсуждения в тредах, важное выносим в KB через fox-archive форум
- **VSC:** shortcuts Ctrl+Shift+M (MEMORY), Ctrl+Shift+W (workflow), Ctrl+Shift+K (tasks)

## Stable environment facts
- Workspace: ~/.openclaw/workspace/ (git repo с kb/ submodule)
- KB: kb/ (отдельный git repo, история с 67cd191)
- Systems: systems/ (memory-schema.puml, workflow.md, vsc-integration.md, automation-ideas.md)
- Discord: чистая структура (🔥 ОСНОВНОЕ, 📚 DOCS, ⚙️ СЕРВИС)
- VSC: .vscode/settings.json готов, нужны расширения (PlantUML, Markdown, Git Graph, GitLens)

## Unresolved
- Git Auto-Commit не настроена (нужно выбрать способ: hook vs VSC extension)
- Cron scheduler для daily archive (нужно настроить в системе)
- Discord bot команды для экспорта (позже, когда система стабильна)

# TASKS — browser-agent

## Current
- [x] Подготовить структуру browser-agent
- [x] Создать skill gologin-automation
- [x] Описать workflow: Gologin → browser profile → Playwright
- [x] Подготовить установку Gologin на этой машине
- [x] Проверить способ подключения OpenClaw к Gologin-профилю
- [x] Перейти на собственную систему профилей Chromium + Playwright
- [x] Создать реестр профилей
- [x] Создать launcher persistent profile
- [x] Запустить первый профиль `google-main`
- [x] Проверить сохранение сессии после закрытия/повторного запуска
- [x] Добавить слой подключения к уже открытому профилю через CDP
- [x] Реализовать MVP browser control layer
- [x] Добавить text observation layer без screenshot automation
- [x] Добавить runtime state в `runtime/<profile-id>.json`
- [x] Добавить CLI команды navigation / text extraction / interaction / tabs
- [x] Добавить единый wrapper `bin/fox-browser`
- [x] Свести browser CLI в один shell entrypoint

## Later
- [ ] Добавить шаблоны Playwright-скриптов
- [ ] Добавить правила по работе с несколькими профилями
- [ ] Добавить отдельный worklog по браузерной автоматизации
- [ ] Улучшить multi-tab state, если пользователь активно переключает вкладки руками
- [ ] Добавить более надёжные selector hints для сложных SPA
- [ ] Добавить JSON-over-stdin/stdout режим при необходимости
- [ ] Добавить completion/help shortcuts для `fox-browser`, если wrapper станет основным allowlist entry

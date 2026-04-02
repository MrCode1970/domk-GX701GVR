# WORKLOG — browser-agent

## 2026-04-02
- Создана отдельная зона `agents/browser-agent/`
- Решено делать отдельный агент + отдельный skill
- Название skill: `gologin-automation`
- Цель: установка Gologin, работа с профилями, подключение через Playwright, безопасная автоматизация браузера
- Подтверждено: Gologin на Linux = AppImage; free-режим у сервиса неоднозначен, решили не завязываться на него
- Принято новое направление: своя система профилей на Chromium + Playwright persistent context
- Создан реестр профилей: `agents/browser-agent/config/profiles.json`
- Создан launcher: `agents/browser-agent/scripts/launch_profile.py`
- Подготовлена папка хранения профилей: `agents/browser-agent/profiles/`
- Проверен persistent Chromium profile через Playwright
- Прямой вход в Google в таком профиле по-прежнему детектится как небезопасный браузер
- Новый подзадача: найти способ Google-safe запуска/подключения и потом проверить на практике
- Реализация смещена в сторону локального browser control layer поверх уже рабочего persistent launcher
- Добавлен пакет `browser_agent/` с общим кодом launcher/controller/runtime
- `scripts/launch_profile.py` сохранён как рабочий entrypoint; теперь он пишет runtime state и поднимает CDP port
- Добавлен `scripts/browser_control.py` с CLI-командами:
  - `open_url`
  - `current_state`
  - `extract_visible_text`
  - `get_interactive_elements`
  - `click`
  - `type`
  - `press`
  - `wait_for_text`
  - `back`
  - `forward`
  - `reload`
  - `list_tabs`
  - `switch_tab`
- Runtime state пишется в `runtime/<profile-id>.json`
- Для интерактивных элементов сохраняются `last_interactive_elements` + fingerprint страницы
- Защита от stale `index`: если страница изменилась после `get_interactive_elements`, команда возвращает явную ошибку
- Устранена ошибка, при которой control CLI закрывал весь реальный браузер при disconnect
- Обновлена документация `README.md`

## Проверено локально
- `launch_profile.py test --hold-ms 120000` открывает реальный Chrome с persistent profile
- `browser_control.py test current_state` возвращает `profile_id`, `active_tab_id`, `url`, `title`
- `browser_control.py test extract_visible_text --limit 300` извлекает видимый текст страницы
- `browser_control.py test get_interactive_elements` возвращает видимые `link/button/input`
- `browser_control.py test click --index 0` успешно нажимает ссылку на `example.com`
- `browser_control.py test type --label Name --value Alice` записывает значение в input на `data:`-странице
- `browser_control.py test wait_for_text "Example Domain"` работает после исправления `wait_for_function`
- `browser_control.py test list_tabs` и `switch_tab --index 0` работают на живой сессии
- После page change `click --index 0` корректно возвращает ошибку `Page changed since last get_interactive_elements call`

## 2026-04-02 CDP Bugfix
- Найден race: launcher раньше времени писал `session_health=running` и печатал успех до гарантированной готовности CDP HTTP endpoint
- Найдено несоответствие lifecycle-state: по `hold-ms` runtime мог выглядеть живым/idle, хотя launcher уже собирался закрыть browser
- Добавлен preflight на занятый `control_port`
- Добавлен poll readiness для `/json/version` и `/json/list` перед переходом в `running`
- `running` теперь выставляется только после подтверждённой доступности CDP endpoint
- Если CDP не поднялся в timeout, launcher честно падает с `session_health=error`
- `controller.connect()` больше не превращает ранний `ECONNREFUSED` в ложный `disconnected`, если launcher ещё находится в `starting`
- Состояния launcher приведены к более честным: `starting`, `running`, `stopping`, `stopped`, `disconnected`, `error`

## 2026-04-02 Unified CLI
- Добавлен единый shell wrapper `bin/fox-browser`
- `fox-browser` маршрутизирует подкоманды в существующие `launch_profile.py` и `browser_control.py`
- Поддержаны подкоманды:
  - `launch`
  - `state`
  - `open-url`
  - `text`
  - `elements`
  - `click`
  - `type`
  - `press`
  - `wait-text`
  - `back`
  - `forward`
  - `reload`
  - `tabs`
  - `switch-tab`
- `bin/launch-google-main` переведён в thin-wrapper поверх `fox-browser launch google-main`
- `bin/browserctl` оставлен как legacy wrapper к старому формату вызова
- Документация обновлена так, чтобы `fox-browser` был основным entrypoint

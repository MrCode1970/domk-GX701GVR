# browser-agent

Локальная рабочая зона для браузерной автоматизации на базе real Chrome/Chromium + Playwright persistent profiles.

Сейчас здесь есть два слоя:
- persistent-profile launcher для обычного ручного запуска браузера
- text-first browser control layer поверх уже открытого профиля через CDP

Основной entrypoint для shell-использования:
- `agents/browser-agent/bin/fox-browser`

## Что важно
- подтверждённый сценарий `launch_profile.py <profile-id>` сохранён
- профиль остаётся persistent: cookies, local storage и логины живут в `profiles/<profile-id>/`
- control layer не использует скриншоты и не тащит полный DOM без необходимости
- observation строится вокруг `current_state`, `extract_visible_text` и `get_interactive_elements`

## Структура
- `config/profiles.json` — реестр профилей и control ports
- `profiles/<profile-id>/` — persistent user data dir браузера
- `runtime/<profile-id>.json` — in-memory-like state на диске для active tab / last elements / health
- `browser_agent/` — общий Python-код launcher + controller
- `bin/fox-browser` — единый CLI wrapper для launcher + control layer
- `scripts/launch_profile.py` — запуск реального браузера с persistent profile
- `scripts/browser_control.py` — CLI управления уже открытым профилем
- `bin/launch-google-main` — legacy wrapper для быстрого запуска `google-main`
- `bin/browserctl` — legacy wrapper прямого доступа к старому control CLI

## Единый CLI
Базовый способ работы теперь такой:

```bash
cd /home/domk/.openclaw/workspace
agents/browser-agent/bin/fox-browser --help
```

Подкоманды:
- `launch <profile-id> [launcher options]`
- `state <profile-id>`
- `open-url <profile-id> <url>`
- `text <profile-id> [--limit N]`
- `elements <profile-id> [--limit N]`
- `click <profile-id> --index N | --selector CSS | --label TEXT | --text TEXT`
- `type <profile-id> --value TEXT --index N | --selector CSS | --label TEXT | --text TEXT`
- `press <profile-id> <key> [--index N | --selector CSS | --label TEXT]`
- `wait-text <profile-id> <text> [--timeout-ms N]`
- `back <profile-id>`
- `forward <profile-id>`
- `reload <profile-id>`
- `tabs <profile-id>`
- `switch-tab <profile-id> --tab-id ID | --index N`

Опции `launch`:
- `--start-url URL`
- `--control-port PORT`
- `--hold-ms N`
- `--cdp-ready-timeout-ms N`

## Примеры

```bash
agents/browser-agent/bin/fox-browser launch google-main
agents/browser-agent/bin/fox-browser launch google-main --start-url https://mail.google.com
agents/browser-agent/bin/fox-browser state google-main
agents/browser-agent/bin/fox-browser open-url google-main https://mail.google.com
agents/browser-agent/bin/fox-browser text google-main --limit 4000
agents/browser-agent/bin/fox-browser elements google-main --limit 120
agents/browser-agent/bin/fox-browser click google-main --index 0
agents/browser-agent/bin/fox-browser type google-main --label "Поиск в почте" --value "anthropic"
agents/browser-agent/bin/fox-browser press google-main Enter
agents/browser-agent/bin/fox-browser tabs google-main
agents/browser-agent/bin/fox-browser switch-tab google-main --index 1
```

## Legacy entrypoints
- `scripts/launch_profile.py` — низкоуровневый launcher, оставлен для совместимости
- `scripts/browser_control.py` — низкоуровневый control CLI, оставлен для совместимости
- `bin/launch-google-main` — legacy thin-wrapper, теперь вызывает `fox-browser launch google-main`
- `bin/browserctl` — legacy thin-wrapper к старому формату `browser_control.py`

## Что возвращает observation layer
`current_state`:
- `profile_id`
- `active_tab_id`
- `url`
- `title`

`get_interactive_elements`:
- только видимые полезные элементы
- `index`, `kind`, `text`, `label`, `placeholder`, `href`, `selector`, `disabled`, `readonly`

`extract_visible_text`:
- только видимый текст страницы
- с ограничением длины через `--limit`

## Ограничения MVP
- нет screenshot/image automation
- нет full DOM dump
- нет web server
- нет persisted command queue
- `index`-адресация валидна только для того DOM snapshot, для которого был вызван `get_interactive_elements`
- если страница изменилась, control layer честно вернёт ошибку и попросит обновить elements list

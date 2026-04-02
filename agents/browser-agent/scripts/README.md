# scripts

Основной shell entrypoint теперь не здесь, а в `agents/browser-agent/bin/fox-browser`.
Скрипты в этой папке остаются как низкоуровневые Python entrypoints и backward-compatible точки входа.

## launch_profile.py
Запускает Chromium через Playwright в persistent mode.

### Пример
```bash
cd /home/domk/.openclaw/workspace
source .venv/bin/activate
python agents/browser-agent/scripts/launch_profile.py google-main
```

## Идея
Каждый профиль хранится в своей папке `agents/browser-agent/profiles/<profile-id>/`.
Сессии, cookies и local storage сохраняются между запусками.

## browser_control.py
Подключается к уже открытому профилю через CDP и даёт text-first control layer.

### Пример
```bash
cd /home/domk/.openclaw/workspace
source .venv/bin/activate
python agents/browser-agent/scripts/browser_control.py google-main current_state
python agents/browser-agent/scripts/browser_control.py google-main get_interactive_elements
python agents/browser-agent/scripts/browser_control.py google-main click --index 0
```

## Рекомендуемый способ
Вместо прямого вызова этих скриптов использовать:

```bash
agents/browser-agent/bin/fox-browser launch google-main
agents/browser-agent/bin/fox-browser state google-main
agents/browser-agent/bin/fox-browser elements google-main
```

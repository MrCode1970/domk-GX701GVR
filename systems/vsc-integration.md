---
date: 2026-03-31
tags: [vsc, tools, workflow, integration]
status: active
version: 1.1
---

# fox — VSC Integration

Как VS Code становится нашим рабочим местом. Расширения, shortcuts, конфиги.

---

## 🎯 Зачем VSC в этой системе?

**Для вас:**
- 📊 Видеть диаграммы (PlantUML → PNG/SVG)
- 📝 Читать markdown документы красиво
- 🔍 Быстрый поиск по всему kb/
- 📈 Git history визуально (кто что менял)
- ⚡ Shortcuts для быстрого доступа к важным файлам

**Для меня (Лиса):**
- 🛠️ Рабочий инструмент (редактирование KB, системные файлы)
- 📋 Terminal для git команд
- 🔗 Git integration (коммиты прямо из редактора)
- 🎯 Shortcuts для повторяющихся операций
- 🤖 Автоматизация (tasks, extensions)

**Вместе:**
- 🔄 Live sync (изменения видны обоим одновременно если нужно)
- 💬 Comments в markdown (обсуждение прямо в KB)
- 📊 Shared workspace (одно место для всех файлов)

---

## 📦 Расширения (Extensions)

### Must-have (обязательные)

| Расширение | Зачем | Для кого |
|-----------|-------|---------|
| **PlantUML** (`jebbs.plantuml`) | Открывать и рендерить .puml диаграммы | Оба |
| **Markdown All in One** (`yzhang.markdown-all-in-one`) | Красивый markdown, preview, shortcuts | Оба |
| **Git Graph** (`mhutchie.git-graph`) | Визуальная история коммитов | Оба |
| **GitLens** (`eamodio.gitlens`) | Кто что менял (blame, history) | Оба |

### Nice-to-have (опционально, для удобства)

| Расширение | Зачем |
|-----------|-------|
| **Todo Tree** (`gruntfuggly.todo-tree`) | Видеть все TODO в коде |
| **Markdown Preview Enhanced** (`shd101wyy.markdown-preview-enhanced`) | Ещё более красивый preview |
| **Peacock** (`johnpapa.peacock`) | Разные цвета для разных workspace'ов |
| **Thunder Client** или **REST Client** | Если будут API тесты |

---

## ⚙️ Конфиг VSC (settings.json)

Находится в `.vscode/settings.json` (создается автоматически).

**Основные параметры:**

```json
{
  // === GIT ===
  "git.autofetch": true,
  "git.confirmSync": false,
  "git.ignoreLimitWarning": true,

  // === EDITOR ===
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.rulers": [80, 120],
  "editor.wordWrap": "on",
  "editor.fontSize": 12,
  "editor.tabSize": 2,

  // === MARKDOWN ===
  "[markdown]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.wordWrap": "on"
  },

  // === FILES ===
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 1000,
  "files.exclude": {
    "**/.git": false,
    "**/node_modules": true
  },

  // === PLANTUML ===
  "plantuml.render": "PlantUMLServer",
  "plantuml.exportOutDir": "./systems/diagrams/out",

  // === SEARCH ===
  "search.exclude": {
    "**/node_modules": true,
    "**/.git": true
  },

  // === TERMINAL ===
  "terminal.integrated.fontSize": 11,
  "terminal.integrated.defaultProfile.linux": "bash"
}
```

---

## ⌨️ Shortcuts (Keyboard Bindings)

**Для быстрого доступа к важным файлам:**

Открыть `.vscode/keybindings.json` и добавить:

```json
[
  {
    "key": "ctrl+shift+m",
    "command": "vscode.open",
    "args": "${workspaceFolder}/MEMORY.md"
  },
  {
    "key": "ctrl+shift+w",
    "command": "vscode.open",
    "args": "${workspaceFolder}/systems/workflow.md"
  },
  {
    "key": "ctrl+shift+k",
    "command": "vscode.open",
    "args": "${workspaceFolder}/kb/projects/fox/tasks.md"
  },
  {
    "key": "ctrl+shift+t",
    "command": "vscode.open",
    "args": "${workspaceFolder}/WORKLOG.md"
  },
  {
    "key": "ctrl+`",
    "command": "workbench.action.terminal.toggleTerminal"
  }
]
```

**Результат:**
- `Ctrl+Shift+M` → открыть MEMORY.md
- `Ctrl+Shift+W` → открыть workflow.md
- `Ctrl+Shift+K` → открыть tasks.md
- `Ctrl+Shift+T` → открыть WORKLOG.md

---

## 📂 Workspace Structure в VSC

**Рекомендуемая структура для быстрого доступа:**

```text
.vscode/
├── settings.json       ← общие настройки
├── keybindings.json    ← мои shortcuts
└── extensions.json     ← список расширений (опционально)

kb/
├── README.md
├── projects/fox/
│   ├── tasks.md
│   ├── goals.md
│   └── ...
└── ...

systems/
├── diagrams/
│   ├── memory-schema.puml     ← архитектура памяти
│   ├── discord-workflow.puml  ← рабочий поток chat → thread → archive → memory → kb
│   └── thread-lifecycle.puml  ← жизненный цикл отдельного треда
├── workflow.md                ← читать отсюда
├── automation-ideas.md
├── discord-rules.md           ← базовые правила системы
└── vsc-integration.md         ← этот файл

MEMORY.md
WORKLOG.md
```

---

## 🎯 Рабочий процесс в VSC

### Сценарий 1: Я обновляю KB

```text
1. Open VSC
2. Ctrl+Shift+K → открыть tasks.md
3. Редактирую, добавляю новую задачу
4. Ctrl+S → сохраняю
5. Ctrl+` → открыть Terminal
6. git add kb/ && git commit -m "Add: ..."
7. git push (если есть remote)
```

### Сценарий 2: Вы хотите увидеть диаграмму памяти

```text
1. Open VSC
2. Ctrl+P → поиск "memory-schema.puml"
3. Enter → открыть `systems/diagrams/memory-schema.puml`
4. Right-click → "Preview PlantUML Diagram"
5. Видите диаграмму рядом с кодом
```

### Сценарий 3: Проверить историю изменений

```text
1. Открыть файл (например, tasks.md)
2. Открыть Source Control / Git Graph
3. Видеть коммиты для файла
4. Кто менял, когда, что изменилось
```

### Сценарий 4: Найти что-то в KB

```text
1. Ctrl+Shift+F → глобальный поиск
2. Напечатать ключевое слово
3. VSC покажет все файлы где это есть
```

---

## 🤖 VSC Tasks (Автоматизация)

**Создать `.vscode/tasks.json` для часто используемых команд:**

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Git: Add KB & Commit",
      "type": "shell",
      "command": "bash",
      "args": ["-lc", "git add kb/ && git commit -m 'Update: KB changes'"]
    },
    {
      "label": "PlantUML: Export Diagrams",
      "type": "shell",
      "command": "plantuml",
      "args": ["-png", "systems/diagrams/memory-schema.puml", "-o", "systems/diagrams/out/"]
    }
  ]
}
```

**Использование:**

```text
Ctrl+Shift+B → выбрать задачу → выполнить
```

---

## 🔍 Git Integration в VSC

### GitLens
- Hover над строкой → кто последний менял и когда
- История файла и blame view

### Git Graph
- Визуальное дерево коммитов
- Видно ветки, историю, изменения по коммитам

---

## 📊 Для вас: Визуализация

### PlantUML диаграммы

1. Откройте `systems/diagrams/memory-schema.puml`
2. Right-click → `Preview PlantUML Diagram`
3. Видите диаграмму в реальном времени
4. При изменении `.puml` файла диаграмма обновляется автоматически
5. При желании можно экспортировать PNG/SVG

### Markdown Preview

1. Откройте любой `.md` файл, например `systems/workflow.md`
2. `Ctrl+K V` → Preview рядом с кодом
3. Видите форматированный текст

---

## 🚀 Первый запуск (Checklist)

- [ ] Открыть папку `~/.openclaw/workspace`
- [ ] Установить расширения: PlantUML, Markdown All in One, Git Graph, GitLens
- [ ] Проверить `.vscode/settings.json`
- [ ] При желании добавить `.vscode/keybindings.json`
- [ ] Открыть Terminal и выполнить `git status`
- [ ] Убедиться, что видны `kb/`, `systems/`, `MEMORY.md`
- [ ] Открыть `systems/diagrams/memory-schema.puml` → Preview
- [ ] Открыть `systems/workflow.md` → Preview

---

## 💡 Главное различие

- `.vscode/` = **настройки редактора**
- `systems/diagrams/` = **сами схемы**
- `kb/.git` = **история знаний**

То есть `.vscode` не хранит диаграммы. Он помогает их удобно открывать и показывать.

---

## 📝 Итого

**VSC = рабочее место.**

- схемы живут в `systems/diagrams/`
- настройки живут в `.vscode/`
- знания живут в `kb/`
- системные описания живут в `systems/`

Так чище, понятнее и проще расти дальше.

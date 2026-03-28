# OpenClaw Audit Worklog

## 2026-03-24 18:46 GMT+2

### Проведенные проверки

1. ✅ OpenClaw версия: 2026.3.23-2
2. ✅ Основной конфиг: ~/.openclaw/openclaw.json
3. ✅ Auth profiles: openrouter:default (API key valid)
4. ✅ Models: checked in models.json
5. ✅ Agent config: main agent, workspace path
6. ✅ Tools & Plugins: Web search (Brave), 51 skills
7. ✅ Security settings: Gateway (local), Sandbox (not explicit)
8. ✅ Channels: Telegram enabled
9. ✅ Hooks: All standard enabled
10. ✅ Status: `openclaw status` output analyzed

### Найденные проблемы

**CRITICAL (2):**
1. 120B Nemotron model в fallback chain — слишком мало параметров, небезопасно
2. gpt-5-codex model — не найдена в стандартных OpenAI, может быть ошибкой

**WARNING (2):**
3. Нет явного sandbox.mode — должно быть "all" для безопасности
4. Несоответствие primary model между defaults и main agent

**CLEANUP (1):**
5. BOOTSTRAP.md все еще существует (должен быть удален)

### Что хорошо

- ✅ Gateway локальный и безопасный
- ✅ API ключ действителен
- ✅ Web tools работают
- ✅ Skills загружены
- ✅ Session memory включена
- ✅ Approvals включены

### Рекомендации (приоритет)

1. **Priority 1:** Удалить 120B и gpt-5-codex из fallback chain
   - Оставить только: openrouter/free, claude-haiku-4.5
   
2. **Priority 2:** Добавить `sandbox.mode: "all"` в agents.defaults

3. **Priority 3:** Унифицировать primary model на "auto" везде

4. **Priority 4:** Удалить BOOTSTRAP.md (`rm ~/.openclaw/workspace/BOOTSTRAP.md`)

5. **Priority 5:** (Optional) Добавить Anthropic/Gemini провайдеры если есть keys

### Статус

✅ Аудит завершен. Конфиг работает, но нуждается в чистке.

Полный отчет: `audit/openclaw-config-audit.md`

Ожидаю подтверждения на применение исправлений.

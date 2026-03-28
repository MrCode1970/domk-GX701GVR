# OpenClaw Configuration Audit

**Дата:** 2026-03-24 18:46 GMT+2  
**Version:** 2026.3.23-2 (7ffe7e4)  
**Host:** domk-GX701GVR (Linux 6.8.0-106, x86_64)

---

## 📋 Summary

**Status:** ⚠️ **Mostly OK, but needs attention in 3 areas**

OpenClaw установлен и работает. Основная конфигурация хороша, но есть:
- 2 критичных security warning
- 1 fallback model слишком мал для безопасности
- Неиспользуемые модели в конфигурации
- Нет явного указания sandbox режима

---

## 🔧 Current Configuration

### Основные пути

| Параметр | Значение | Статус |
|---|---|---|
| **OpenClaw version** | 2026.3.23-2 | ✅ Latest |
| **Installation path** | ~/.npm-global/bin/openclaw | ✅ |
| **Config path** | ~/.openclaw/openclaw.json | ✅ |
| **Workspace** | ~/.openclaw/workspace | ✅ |
| **Gateway port** | 18789 (localhost only) | ✅ |

### Auth & Providers

| Параметр | Значение | Статус | Проблема |
|---|---|---|---|
| **Auth profiles** | openrouter:default | ✅ | - |
| **Provider** | OpenRouter | ✅ | - |
| **API Key** | sk-or-v1-... | ✅ | Key valid, no errors |
| **OpenAI** | Not configured | ⚠️ | Not configured |
| **Anthropic** | Not configured | ⚠️ | Not configured |
| **Gemini** | Not configured | ⚠️ | Not configured (skill available) |

### Models Configuration

| Model | Type | Context | MaxTokens | Status | Notes |
|---|---|---|---|---|---|
| **openrouter/auto** | Primary | 200k | 8192 | ✅ Good | Default, flexible |
| **openrouter/free** | Fallback #1 | ? | ? | ✅ Good | Free tier option |
| **openrouter/nvidia/nemotron-3-super-120b-a12b:free** | Fallback #2 | ? | ? | 🚨 UNSAFE | **120B params — too small!** |
| **openrouter/openai/gpt-5-codex** | Fallback #3 | ? | ? | ⚠️ Unknown | Not found in standard OpenAI |
| **openrouter/anthropic/claude-haiku-4.5** | Fallback #4 | ? | ? | ✅ Good | Claude Haiku, reliable |

### Agent Configuration

| Параметр | Значение | Статус |
|---|---|---|
| **Default agent** | "main" | ✅ |
| **Primary model** | openrouter/free | ✅ (was: openrouter/auto) |
| **Fallbacks** | 4 models | ⚠️ See above |
| **Workspace path** | ~/.openclaw/workspace | ✅ |
| **Sessions active** | 2 | ✅ |
| **Bootstrap files** | 1 present | ✅ |

### Tools & Plugins

| Компонент | Status | Config |
|---|---|---|
| **Web search** | ✅ Enabled | Brave API (key present) |
| **Web fetch** | ✅ Enabled | Standard |
| **Browser/Playwright** | ✅ Enabled (implicit) | No explicit config |
| **Skills** | ✅ 51 skills installed | npm manager |
| **Native commands** | ✅ auto | |
| **Native skills** | ✅ auto | |

### Security & Sandbox

| Параметр | Значение | Status |
|---|---|---|
| **Gateway bind** | loopback (127.0.0.1) | ✅ Good (local only) |
| **Gateway auth** | token (51d78ebf...) | ✅ |
| **Sandbox mode** | **Not explicitly set** | ⚠️ |
| **Tailscale** | off | ✅ |
| **Node deny commands** | 6 commands blocked | ✅ |
| **Exec approvals** | Enabled (default) | ✅ |

### Channels

| Канал | Status | Config |
|---|---|---|
| **Telegram** | ✅ Enabled | Bot token present, DMPolicy: pairing |
| **Discord** | ✗ Not enabled | Skill available |
| **WhatsApp** | ✗ Not enabled | Not configured |
| **Email** | ✗ Not enabled | Not configured |

### Hooks & Extensions

| Hook | Status | Config |
|---|---|---|
| **boot-md** | ✅ Enabled | Loads markdown on startup |
| **bootstrap-extra-files** | ✅ Enabled | |
| **command-logger** | ✅ Enabled | Logs executed commands |
| **session-memory** | ✅ Enabled | Persistent session memory |

---

## 🚨 Critical Issues (Security Audit)

### Issue #1: Small Model (120B) in Fallback Chain
**Severity:** 🚨 CRITICAL

```
Model: openrouter/nvidia/nemotron-3-super-120b-a12b:free
Size: 120B parameters (very small)
Risk: Can produce unsafe or low-quality completions
Location: agents.defaults.model.fallbacks[1]
```

**Impact:** 
- Если все основные модели недоступны, может упасть на 120B модель
- Нет гарантии качества или безопасности
- Не рекомендуется для production

**Fix:** Удалить или переместить в самый конец

---

### Issue #2: gpt-5-codex Model
**Severity:** ⚠️ WARNING

```
Model: openrouter/openai/gpt-5-codex
Status: Not found in standard OpenAI
Context: Unknown
```

**Impact:**
- Модель может не существовать или быть недоступной
- Если упадет в эту fallback, может привести к ошибке

**Fix:** Проверить доступность через OpenRouter или удалить

---

### Issue #3: No Explicit Sandbox Configuration
**Severity:** ⚠️ WARNING

```
Current: No explicit sandbox.mode set in agents.defaults
Implication: Small models (if fallback reaches them) run without sandboxing
Recommendation: Set sandbox.mode="all" for safety
```

---

## ⚠️ Other Issues

### #4: Conflicting Primary Model
**Severity:** 🟡 INFO

```
agents.defaults.model.primary: "openrouter/auto"
agents.list[0].model.primary: "openrouter/free"

Inconsistency: Main agent uses "free" instead of "auto"
Should be: Both should use "auto" for consistency
```

---

### #5: Unused Auth Profiles / Providers
**Severity:** 🟢 MINOR

```
Not configured:
- OpenAI (openai:*)
- Anthropic (anthropic:*)
- Gemini (google:*)

Note: They're optional, but if you want fallback providers, set them up.
```

---

### #6: Bootstrap File Present
**Severity:** 🟢 INFO (but check it)

```
Status: 1 bootstrap file present
Location: ~/.openclaw/workspace/BOOTSTRAP.md (should be deleted per instructions)
Action: Verify you deleted BOOTSTRAP.md per instructions
```

Проверю:

---

## ✅ What's Working Well

- ✅ **Gateway:** Local, secure, reachable (50ms)
- ✅ **Auth:** OpenRouter API key valid, 0 errors
- ✅ **Web tools:** Brave search enabled with API key
- ✅ **Skills:** 51 skills installed, ready to use
- ✅ **Commands:** Native commands & skills auto-enabled
- ✅ **Channels:** Telegram configured and working
- ✅ **Memory:** Session memory enabled
- ✅ **Hooks:** All standard hooks enabled
- ✅ **Approval system:** Default exec approvals enabled

---

## 📋 Recommended Fixes (Priority Order)

### Priority 1 (DO FIRST): Fix Fallback Chain
**Action:** Remove or demote 120B model

Current state:
```json
"fallbacks": [
  "openrouter/free",
  "openrouter/nvidia/nemotron-3-super-120b-a12b:free",  // ← DELETE THIS
  "openrouter/openai/gpt-5-codex",
  "openrouter/anthropic/claude-haiku-4.5"
]
```

Better:
```json
"fallbacks": [
  "openrouter/free",
  "openrouter/anthropic/claude-haiku-4.5"
]
```

**Why:** Small models are unsafe for uncontrolled execution. Keep only proven, reliable fallbacks.

---

### Priority 2 (DO SECOND): Add Explicit Sandbox
**Action:** Set sandbox.mode explicitly

Add to `agents.defaults`:
```json
"sandbox": {
  "mode": "all"
}
```

**Why:** Makes execution safer, especially if fallback models are used.

---

### Priority 3 (DO THIRD): Unify Primary Model
**Action:** Make "main" agent use "auto" instead of "free"

Change:
```json
"agents": {
  "list": [
    {
      "id": "main",
      "model": {
        "primary": "openrouter/auto",  // ← Change from "free" to "auto"
        "fallbacks": [...]
      }
    }
  ]
}
```

**Why:** Consistency. "auto" picks best available, "free" limits to free tier.

---

### Priority 4 (OPTIONAL): Add Backup Providers
**Action:** If you want fallback to other providers, configure them

Example (add to `auth.profiles`):
```json
"anthropic:default": {
  "provider": "anthropic",
  "mode": "api_key",
  "key": "sk-ant-..."  // Add if you have key
}
```

**Why:** Optional. Only if you want redundancy beyond OpenRouter.

---

### Priority 5 (CLEANUP): Check Bootstrap
**Action:** Verify BOOTSTRAP.md is deleted

```bash
ls -la ~/.openclaw/workspace/BOOTSTRAP.md
```

If exists: should have been deleted after initial setup.

---

## 🔍 Config Patch (Ready to Apply)

If you approve, I can apply this patch to `openclaw.json`:

```diff
--- a/agents.defaults.model.fallbacks
+++ b/agents.defaults.model.fallbacks
@@ -1,8 +1,6 @@
 [
   "openrouter/free",
-  "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
-  "openrouter/openai/gpt-5-codex",
   "openrouter/anthropic/claude-haiku-4.5"
 ]

--- a/agents.list[0].model.primary
+++ b/agents.list[0].model.primary
@@ -1 +1 @@
-"openrouter/free"
+"openrouter/auto"

+++ b/agents.defaults.sandbox
@@ -0,0 +1,3 @@
+  "sandbox": {
+    "mode": "all"
+  }
```

---

## 📝 Decision Points for You

### Do you want to:

1. **Apply all Priority 1-3 fixes?** (Recommended)
   - Remove unsafe 120B model
   - Add explicit sandbox
   - Unify model usage
   
2. **Add backup providers (Priority 4)?**
   - Only if you have Anthropic or Gemini keys
   
3. **Keep current config as-is?**
   - Works, but has security warnings

---

**Next:** Confirm which fixes you want, then I'll apply them.

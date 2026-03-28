# Investigation: openrouter/openai/gpt-5-codex

**Date:** 2026-03-24 18:54 GMT+2

---

## Status

**Verdict: ✅ SAFE TO KEEP**

---

## Full Analysis

### 1. Model Reference

```
Full: openrouter/openai/gpt-5-codex
Provider: openrouter
Model ID: openai/gpt-5-codex
```

### 2. Config Presence

✅ **In agents.defaults.models:** YES
```json
"openrouter/openai/gpt-5-codex": {}
```
(Empty definition — placeholder/metadata only)

### 3. Catalog Lookup

❌ **In models.json catalog:** NO

```
Total OpenRouter models in catalog: 3
- auto (OpenRouter Auto)
- openrouter/hunter-alpha
- openrouter/healer-alpha
- (No gpt-5-codex)
```

**Reason:** Local catalog in `~/.openclaw/agents/main/agent/models.json` only has 3 models. It's a snapshot, not complete OpenRouter catalog.

### 4. Runtime Resolution

**How OpenClaw handles unknown models:**

```
When model "openrouter/openai/gpt-5-codex" is needed:
├─ Step 1: Check local catalog
│  └─ NOT found → continue
├─ Step 2: Try OpenRouter API directly
│  ├─ If available: use it ✅
│  └─ If unavailable: fallback ⟹ Step 3
└─ Step 3: Use next model in fallback chain
   └─ Next: openrouter/anthropic/claude-haiku-4.5
```

### 5. Possible Explanations

| Scenario | Evidence | Probability | Impact |
|---|---|---|---|
| **New model, not in local catalog yet** | gpt-5-codex is real but catalog outdated | High | Works if available on OpenRouter |
| **Runtime resolution** | OpenClaw supports direct model refs | High | Safe — fallback mechanism |
| **Experimental/Testing** | Config predates real availability | Medium | Fails gracefully, uses fallback |
| **Invalid model ID** | Wrong format or typo | Low | Fails → fallback to next |

### 6. Safety Assessment

**Risk Level:** 🟢 LOW

**Why:**
- Fallback chain is designed for exactly this
- Worst case: model request fails, immediately uses claude-haiku-4.5
- No data loss or breaking changes
- Empty definition `{}` means no special config assumed

### 7. Recommendation

**Action:** KEEP IT

**Rationale:**
- Harmless placeholder in fallback chain
- If OpenRouter supports it, will work
- If not, silently falls back to next model
- Attempt-then-fallback is safe design

**Future Actions:**
- Monitor if fallback triggers (check logs)
- Update models.json when availability confirmed
- Keep claude-haiku-4.5 as final fallback (it's reliable)

---

## Conclusion

✅ **NOT A PROBLEM**

The model is:
- In config (metadata placeholder)
- In fallback chain (will attempt)
- NOT in local catalog (expected — not all models cataloged locally)
- Safe if absent (falls back to next)

No action needed. Safe to keep.

"""Browser controller on raw CDP — no Playwright dependency."""

import argparse
import json
import time
from typing import Any

from browser_agent.common import read_runtime_state, write_runtime_state
from browser_agent.engines.cdp import CDPBrowser, CDPError, CDPSession


class BrowserControlError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Interactive elements JS (reused from original controller)
# ---------------------------------------------------------------------------

INTERACTIVE_ELEMENTS_JS = """
(maxItems) => {
  const candidates = Array.from(document.querySelectorAll([
    'a[href]', 'button', 'input:not([type="hidden"])', 'select', 'textarea',
    '[role="button"]', '[role="link"]', '[contenteditable="true"]', 'summary'
  ].join(',')));

  const isVisible = (element) => {
    const style = window.getComputedStyle(element);
    if (!style) return false;
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    if (rect.bottom < 0 || rect.right < 0) return false;
    return true;
  };

  const textOf = (value) => {
    if (!value) return null;
    const compact = value.replace(/\\s+/g, ' ').trim();
    return compact || null;
  };

  const escape = (value) => {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return value.replace(/([ #;?%&,.+*~':"!^$\\[\\]()=>|\\/@])/g, '\\\\$1');
  };

  const cssPath = (element) => {
    if (!(element instanceof Element)) return null;
    if (element.id) return '#' + escape(element.id);
    const parts = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.getAttribute('name')) {
        selector += '[name="' + escape(current.getAttribute('name')) + '"]';
        parts.unshift(selector);
        break;
      }
      const parent = current.parentElement;
      if (!parent) break;
      const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
      if (siblings.length > 1) {
        const index = siblings.indexOf(current) + 1;
        selector += ':nth-of-type(' + index + ')';
      }
      parts.unshift(selector);
      current = parent;
    }
    return parts.length ? parts.join(' > ') : null;
  };

  const labelOf = (element) => {
    const aria = textOf(element.getAttribute('aria-label'));
    if (aria) return aria;
    if ('labels' in element && element.labels && element.labels.length) {
      const labels = Array.from(element.labels)
        .map(item => textOf(item.innerText || item.textContent))
        .filter(Boolean);
      if (labels.length) return labels.join(' | ');
    }
    return null;
  };

  const kindOf = (element) => {
    const tag = element.tagName.toLowerCase();
    if (tag === 'a' || element.getAttribute('role') === 'link') return 'link';
    if (tag === 'button' || element.getAttribute('role') === 'button' || tag === 'summary') return 'button';
    if (tag === 'textarea') return 'textarea';
    if (tag === 'select') return 'select';
    if (tag === 'input') return 'input';
    if (element.getAttribute('contenteditable') === 'true') return 'editable';
    return tag;
  };

  const result = [];
  for (const element of candidates) {
    if (!isVisible(element)) continue;
    const text = textOf(element.innerText || element.textContent || element.value);
    const label = labelOf(element);
    const placeholder = textOf(element.getAttribute('placeholder'));
    const href = element instanceof HTMLAnchorElement ? element.href : null;
    const selector = cssPath(element);
    result.push({
      kind: kindOf(element), text, label, placeholder, href, selector,
      disabled: !!element.disabled, readonly: !!element.readOnly,
    });
    if (result.length >= maxItems) break;
  }
  return result.map((item, index) => ({ index, ...item }));
}
"""

# ---------------------------------------------------------------------------
# JS helpers for element interaction
# ---------------------------------------------------------------------------

CLICK_BY_SELECTOR_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) throw new Error('Element not found: ' + selector);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  el.click();
  return true;
}
"""

CLICK_BY_TEXT_JS = """
(text) => {
  const clickable = [...document.querySelectorAll('button, a, [role="button"], [role="link"], summary')];
  const inputs = [...document.querySelectorAll('input[type="submit"], input[type="button"]')];
  let el = clickable.find(e => (e.textContent || '').trim() === text)
        || clickable.find(e => (e.textContent || '').trim().includes(text))
        || inputs.find(e => e.value === text)
        || inputs.find(e => (e.getAttribute('aria-label') || '') === text);
  if (!el) throw new Error('No element with text: ' + text);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  el.click();
  return true;
}
"""

CLICK_BY_LABEL_JS = """
(label) => {
  let el = document.querySelector('[aria-label="' + label + '"]');
  if (!el) {
    const labels = [...document.querySelectorAll('label')];
    const labelEl = labels.find(l => (l.textContent || '').trim() === label);
    if (labelEl && labelEl.htmlFor) el = document.getElementById(labelEl.htmlFor);
    if (!el && labelEl) el = labelEl.querySelector('input, select, textarea');
  }
  if (!el) el = document.querySelector('[placeholder="' + label + '"]');
  if (!el) throw new Error('No element with label: ' + label);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  el.click();
  return true;
}
"""

FILL_JS = """
(selector, value, clear) => {
  const el = document.querySelector(selector);
  if (!el) throw new Error('Element not found: ' + selector);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  el.focus();
  if (clear || true) {
    if (el.isContentEditable) {
      el.textContent = '';
    } else {
      el.value = '';
    }
    el.dispatchEvent(new Event('input', {bubbles: true}));
  }
  if (el.isContentEditable) {
    el.textContent = value;
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  return true;
}
"""

FOCUS_BY_SELECTOR_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) throw new Error('Element not found: ' + selector);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  el.focus();
  return true;
}
"""

FOCUS_BY_LABEL_JS = """
(label) => {
  let el = document.querySelector('[aria-label="' + label + '"]');
  if (!el) {
    const labels = [...document.querySelectorAll('label')];
    const labelEl = labels.find(l => (l.textContent || '').trim() === label);
    if (labelEl && labelEl.htmlFor) el = document.getElementById(labelEl.htmlFor);
    if (!el && labelEl) el = labelEl.querySelector('input, select, textarea');
  }
  if (!el) el = document.querySelector('[placeholder="' + label + '"]');
  if (!el) throw new Error('No element with label: ' + label);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  el.focus();
  return true;
}
"""

VISIBLE_TEXT_JS = """
(() => {
  const text = document.body ? document.body.innerText : '';
  return text.replace(/\\s+/g, ' ').trim();
})()
"""


# ---------------------------------------------------------------------------
# CLI parser (same interface as original controller)
# ---------------------------------------------------------------------------

def add_target_args(parser: argparse.ArgumentParser, allow_text: bool = True) -> None:
    parser.add_argument("--index", type=int)
    parser.add_argument("--selector")
    parser.add_argument("--label")
    if allow_text:
        parser.add_argument("--text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Browser control CLI (raw CDP engine)."
    )
    parser.add_argument("profile_id", help="Profile id from config/profiles.json")
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("open_url")
    cmd.add_argument("url")
    cmd.add_argument("--timeout-ms", type=int, default=15000)

    sub.add_parser("current_state")

    cmd = sub.add_parser("extract_visible_text")
    cmd.add_argument("--limit", type=int, default=4000)

    cmd = sub.add_parser("get_interactive_elements")
    cmd.add_argument("--limit", type=int, default=80)

    cmd = sub.add_parser("click")
    add_target_args(cmd)
    cmd.add_argument("--timeout-ms", type=int, default=10000)

    cmd = sub.add_parser("type")
    add_target_args(cmd)
    cmd.add_argument("--value", required=True)
    cmd.add_argument("--clear", action="store_true")
    cmd.add_argument("--timeout-ms", type=int, default=10000)

    cmd = sub.add_parser("press")
    cmd.add_argument("key")
    add_target_args(cmd, allow_text=False)

    cmd = sub.add_parser("wait_for_text")
    cmd.add_argument("text")
    cmd.add_argument("--timeout-ms", type=int, default=15000)

    sub.add_parser("back")
    sub.add_parser("forward")
    sub.add_parser("reload")
    sub.add_parser("list_tabs")

    cmd = sub.add_parser("switch_tab")
    cmd.add_argument("--tab-id")
    cmd.add_argument("--index", type=int)

    return parser


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect(profile_id: str) -> tuple[CDPBrowser, dict]:
    runtime = read_runtime_state(profile_id)
    port = runtime.get("control_port")
    if not port:
        raise BrowserControlError(
            f"Profile '{profile_id}' has no control port. Launch the profile first."
        )
    browser = CDPBrowser(port)
    try:
        browser.connect()
        return browser, runtime
    except CDPError as exc:
        current_health = runtime.get("session_health")
        next_health = (
            current_health
            if current_health in {"starting", "error", "stopping", "stopped"}
            else "disconnected"
        )
        write_runtime_state(profile_id, {"session_health": next_health, "last_error": str(exc)})
        raise BrowserControlError(
            f"Could not connect to profile '{profile_id}' on port {port}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Target / tab helpers
# ---------------------------------------------------------------------------

def tab_snapshot(target: dict, index: int) -> dict:
    return {
        "tab_id": target["id"],
        "index": index,
        "url": target.get("url", ""),
        "title": target.get("title", ""),
    }


def pick_active_target(
    profile_id: str, browser: CDPBrowser, runtime: dict
) -> tuple[CDPSession, dict, list[dict]]:
    targets = browser.list_targets()
    if not targets:
        raise BrowserControlError("No open tabs")

    tabs = [tab_snapshot(t, i) for i, t in enumerate(targets)]
    wanted = runtime.get("active_tab_id")

    for target, tab in zip(targets, tabs):
        if tab["tab_id"] == wanted:
            session = browser.page_session(tab["tab_id"])
            return session, tab, tabs

    # Default to first
    target = targets[0]
    tab = tabs[0]
    session = browser.page_session(tab["tab_id"])
    write_runtime_state(profile_id, {
        "active_tab_id": tab["tab_id"],
        "url": tab["url"],
        "title": tab["title"],
        "session_health": "running",
    })
    return session, tab, tabs


def page_fingerprint(session: CDPSession, tab_id: str) -> dict:
    return {
        "tab_id": tab_id,
        "url": session.get_url(),
        "title": session.get_title(),
    }


def update_state(profile_id: str, session: CDPSession, tab_id: str, **extra) -> dict:
    payload = {
        "active_tab_id": tab_id,
        "url": session.get_url(),
        "title": session.get_title(),
        "session_health": "running",
        "last_error": None,
    }
    payload.update(extra)
    return write_runtime_state(profile_id, payload)


# ---------------------------------------------------------------------------
# Element targeting (replaces Playwright locators)
# ---------------------------------------------------------------------------

def resolve_target_selector(
    profile_id: str, session: CDPSession, tab_id: str, args, command: str
) -> tuple[str | None, str]:
    """Returns (css_selector, method) for the targeted element."""
    selectors = [
        bool(getattr(args, "index", None) is not None),
        bool(getattr(args, "selector", None)),
        bool(getattr(args, "label", None)),
        bool(getattr(args, "text", None)),
    ]
    if sum(selectors) != 1:
        raise BrowserControlError(
            f"{command} requires exactly one: --index, --selector, --label, or --text"
        )

    if getattr(args, "index", None) is not None:
        runtime = read_runtime_state(profile_id)
        cached = runtime.get("last_interactive_elements") or []
        fp = runtime.get("last_elements_fingerprint") or {}
        current = page_fingerprint(session, tab_id)
        if fp.get("tab_id") != current["tab_id"] or fp.get("url") != current["url"]:
            raise BrowserControlError(
                "Page changed since last get_interactive_elements. Refresh first."
            )
        idx = args.index
        if idx < 0 or idx >= len(cached):
            raise BrowserControlError(f"Index {idx} out of range (0..{len(cached)-1})")
        sel = cached[idx].get("selector")
        if not sel:
            raise BrowserControlError(f"Element at index {idx} has no selector")
        return sel, "selector"

    if getattr(args, "selector", None):
        return args.selector, "selector"

    if getattr(args, "label", None):
        return args.label, "label"

    return args.text, "text"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def command_current_state(profile_id: str, browser: CDPBrowser, runtime: dict) -> dict:
    session, tab, tabs = pick_active_target(profile_id, browser, runtime)
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(), "tab_count": len(tabs),
    }


def command_open_url(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    session.navigate(args.url)
    time.sleep(1)  # let page start loading
    session.wait_for("document.readyState === 'complete'", timeout_ms=args.timeout_ms)
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
    }


def command_extract_visible_text(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    text = session.evaluate(VISIBLE_TEXT_JS)
    limited = (text or "")[:args.limit]
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
        "text": limited, "truncated": len(text or "") > len(limited),
        "text_length": len(text or ""),
    }


def command_get_interactive_elements(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    elements = session.call_function(INTERACTIVE_ELEMENTS_JS, [args.limit])
    fp = page_fingerprint(session, tab["tab_id"])
    update_state(
        profile_id, session, tab["tab_id"],
        last_interactive_elements=elements,
        last_elements_fingerprint=fp,
    )
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
        "elements": elements, "count": len(elements),
    }


def command_click(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    value, method = resolve_target_selector(profile_id, session, tab["tab_id"], args, "click")

    if method == "selector":
        session.call_function(CLICK_BY_SELECTOR_JS, [value])
    elif method == "label":
        session.call_function(CLICK_BY_LABEL_JS, [value])
    elif method == "text":
        session.call_function(CLICK_BY_TEXT_JS, [value])

    time.sleep(0.3)
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
    }


def command_type(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    value, method = resolve_target_selector(profile_id, session, tab["tab_id"], args, "type")

    if method == "selector":
        session.call_function(FILL_JS, [value, args.value, bool(args.clear)])
    elif method == "label":
        session.call_function(FOCUS_BY_LABEL_JS, [value])
        if args.clear:
            session.evaluate("document.activeElement.value = ''")
            session.evaluate("document.activeElement.dispatchEvent(new Event('input', {bubbles: true}))")
        session.insert_text(args.value)
        session.evaluate("document.activeElement.dispatchEvent(new Event('input', {bubbles: true}))")
        session.evaluate("document.activeElement.dispatchEvent(new Event('change', {bubbles: true}))")
    elif method == "text":
        # text target doesn't make sense for type, but handle gracefully
        raise BrowserControlError("Use --selector, --index, or --label for type command")

    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
    }


def command_press(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)

    has_target = any(
        getattr(args, attr, None) for attr in ("selector", "label")
    ) or getattr(args, "index", None) is not None

    if has_target:
        value, method = resolve_target_selector(profile_id, session, tab["tab_id"], args, "press")
        if method == "selector":
            session.call_function(FOCUS_BY_SELECTOR_JS, [value])
        elif method == "label":
            session.call_function(FOCUS_BY_LABEL_JS, [value])

    session.dispatch_key(args.key)
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
    }


def command_wait_for_text(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    needle = json.dumps(args.text)
    session.wait_for(
        f"(document.body ? document.body.innerText : '').includes({needle})",
        timeout_ms=args.timeout_ms,
    )
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
        "text_found": args.text,
    }


def simple_navigation(profile_id: str, browser: CDPBrowser, runtime: dict, action: str) -> dict:
    session, tab, _ = pick_active_target(profile_id, browser, runtime)
    if action == "back":
        session.evaluate("history.back()")
    elif action == "forward":
        session.evaluate("history.forward()")
    elif action == "reload":
        session.reload()
    time.sleep(1)
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
    }


def command_list_tabs(profile_id: str, browser: CDPBrowser, runtime: dict) -> dict:
    session, tab, tabs = pick_active_target(profile_id, browser, runtime)
    update_state(profile_id, session, tab["tab_id"])
    return {"ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"], "tabs": tabs}


def command_switch_tab(profile_id: str, browser: CDPBrowser, runtime: dict, args) -> dict:
    if args.tab_id is None and args.index is None:
        raise BrowserControlError("switch_tab requires --tab-id or --index")

    targets = browser.list_targets()
    tabs = [tab_snapshot(t, i) for i, t in enumerate(targets)]
    chosen = None

    if args.tab_id is not None:
        for target, tab in zip(targets, tabs):
            if tab["tab_id"] == args.tab_id:
                chosen = (target, tab)
                break
    elif args.index is not None and 0 <= args.index < len(targets):
        chosen = (targets[args.index], tabs[args.index])

    if not chosen:
        raise BrowserControlError("Requested tab not found")

    target, tab = chosen
    browser.activate_target(tab["tab_id"])
    session = browser.page_session(tab["tab_id"])
    update_state(profile_id, session, tab["tab_id"])
    return {
        "ok": True, "profile_id": profile_id, "active_tab_id": tab["tab_id"],
        "url": session.get_url(), "title": session.get_title(),
    }


# ---------------------------------------------------------------------------
# Dispatch + main
# ---------------------------------------------------------------------------

def json_print(payload: dict, exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


def execute(profile_id: str, args) -> dict:
    browser, runtime = connect(profile_id)
    try:
        cmd = args.command
        if cmd == "current_state":
            return command_current_state(profile_id, browser, runtime)
        if cmd == "open_url":
            return command_open_url(profile_id, browser, runtime, args)
        if cmd == "extract_visible_text":
            return command_extract_visible_text(profile_id, browser, runtime, args)
        if cmd == "get_interactive_elements":
            return command_get_interactive_elements(profile_id, browser, runtime, args)
        if cmd == "click":
            return command_click(profile_id, browser, runtime, args)
        if cmd == "type":
            return command_type(profile_id, browser, runtime, args)
        if cmd == "press":
            return command_press(profile_id, browser, runtime, args)
        if cmd == "wait_for_text":
            return command_wait_for_text(profile_id, browser, runtime, args)
        if cmd in {"back", "forward", "reload"}:
            return simple_navigation(profile_id, browser, runtime, cmd)
        if cmd == "list_tabs":
            return command_list_tabs(profile_id, browser, runtime)
        if cmd == "switch_tab":
            return command_switch_tab(profile_id, browser, runtime, args)
        raise BrowserControlError(f"Unknown command: {cmd}")
    finally:
        browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return json_print(execute(args.profile_id, args))
    except BrowserControlError as exc:
        write_runtime_state(args.profile_id, {"last_error": str(exc)})
        return json_print({"ok": False, "error": "browser_control_error", "message": str(exc)}, 1)
    except CDPError as exc:
        write_runtime_state(args.profile_id, {"last_error": str(exc)})
        return json_print({"ok": False, "error": "cdp_error", "message": str(exc)}, 1)
    except Exception as exc:
        write_runtime_state(args.profile_id, {"last_error": f"Unexpected: {exc}"})
        return json_print({"ok": False, "error": "unexpected_error", "message": str(exc)}, 1)

import argparse
import json
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Error, Page, TimeoutError, sync_playwright

from browser_agent.common import read_runtime_state, write_runtime_state


class BrowserControlError(RuntimeError):
    pass


def json_print(payload: dict[str, Any], exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Browser control CLI for a running browser-agent profile."
    )
    parser.add_argument("profile_id", help="Profile id from config/profiles.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("open_url", help="Navigate current tab to a URL")
    command.add_argument("url")
    command.add_argument("--timeout-ms", type=int, default=15000)

    subparsers.add_parser("current_state", help="Show current profile/tab state")

    command = subparsers.add_parser(
        "extract_visible_text", help="Return visible page text with a length limit"
    )
    command.add_argument("--limit", type=int, default=4000)

    command = subparsers.add_parser(
        "get_interactive_elements", help="List visible links/buttons/inputs"
    )
    command.add_argument("--limit", type=int, default=80)

    command = subparsers.add_parser("click", help="Click an element")
    add_target_args(command)
    command.add_argument("--timeout-ms", type=int, default=10000)

    command = subparsers.add_parser("type", help="Type into an element")
    add_target_args(command)
    command.add_argument("--value", required=True)
    command.add_argument("--clear", action="store_true")
    command.add_argument("--timeout-ms", type=int, default=10000)

    command = subparsers.add_parser("press", help="Press a keyboard key")
    command.add_argument("key")
    add_target_args(command, allow_text=False)

    command = subparsers.add_parser("wait_for_text", help="Wait until text appears")
    command.add_argument("text")
    command.add_argument("--timeout-ms", type=int, default=15000)

    subparsers.add_parser("back", help="Navigate back")
    subparsers.add_parser("forward", help="Navigate forward")
    subparsers.add_parser("reload", help="Reload current tab")
    subparsers.add_parser("list_tabs", help="List tabs")

    command = subparsers.add_parser("switch_tab", help="Switch active tab")
    command.add_argument("--tab-id")
    command.add_argument("--index", type=int)

    return parser


def add_target_args(parser: argparse.ArgumentParser, allow_text: bool = True) -> None:
    parser.add_argument("--index", type=int)
    parser.add_argument("--selector")
    parser.add_argument("--label")
    if allow_text:
        parser.add_argument("--text")


def connect(profile_id: str):
    runtime = read_runtime_state(profile_id)
    port = runtime.get("control_port")
    if not port:
        raise BrowserControlError(
            f"Profile '{profile_id}' has no control port. Launch the profile first."
        )

    playwright = sync_playwright().start()
    browser = None
    try:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        contexts = browser.contexts
        if not contexts:
            raise BrowserControlError("Connected browser has no contexts")
        context = contexts[0]
        return playwright, browser, context, runtime
    except Exception as exc:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        playwright.stop()
        current_health = runtime.get("session_health")
        next_health = (
            current_health
            if current_health in {"starting", "error", "stopping", "stopped"}
            else "disconnected"
        )
        write_runtime_state(
            profile_id,
            {
                "session_health": next_health,
                "last_error": str(exc),
            },
        )
        raise BrowserControlError(
            f"Could not connect to profile '{profile_id}' on port {port}: {exc}"
        ) from exc


def disconnect(playwright, browser: Browser) -> None:
    del browser
    playwright.stop()


def get_target_info(page: Page) -> dict[str, Any]:
    try:
        session = page.context.new_cdp_session(page)
        return session.send("Target.getTargetInfo")
    except Exception:
        return {}


def tab_snapshot(page: Page, index: int) -> dict[str, Any]:
    info = get_target_info(page).get("targetInfo", {})
    return {
        "tab_id": info.get("targetId") or f"tab-{index}",
        "index": index,
        "url": page.url,
        "title": safe_title(page),
    }


def list_pages(context: BrowserContext) -> list[Page]:
    return [page for page in context.pages if not page.is_closed()]


def safe_title(page: Page) -> str:
    try:
        return page.title()
    except Exception:
        return ""


def pick_active_page(
    profile_id: str, context: BrowserContext, runtime: dict
) -> tuple[Page, dict[str, Any], list[dict[str, Any]]]:
    pages = list_pages(context)
    if not pages:
        raise BrowserControlError("No open tabs in browser context")

    tabs = [tab_snapshot(page, index) for index, page in enumerate(pages)]
    wanted = runtime.get("active_tab_id")
    for page, tab in zip(pages, tabs):
        if tab["tab_id"] == wanted:
            return page, tab, tabs

    page = pages[0]
    write_runtime_state(
        profile_id,
        {
            "active_tab_id": tabs[0]["tab_id"],
            "url": page.url,
            "title": safe_title(page),
            "session_health": "running",
        },
    )
    return page, tabs[0], tabs


def interactive_elements(page: Page, limit: int) -> list[dict[str, Any]]:
    js = """
    (maxItems) => {
      const candidates = Array.from(document.querySelectorAll([
        'a[href]',
        'button',
        'input:not([type="hidden"])',
        'select',
        'textarea',
        '[role="button"]',
        '[role="link"]',
        '[contenteditable="true"]',
        'summary'
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
        if (element.id) return `#${escape(element.id)}`;
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
          let selector = current.tagName.toLowerCase();
          if (current.getAttribute('name')) {
            selector += `[name="${escape(current.getAttribute('name'))}"]`;
            parts.unshift(selector);
            break;
          }
          const parent = current.parentElement;
          if (!parent) break;
          const siblings = Array.from(parent.children)
            .filter((child) => child.tagName === current.tagName);
          if (siblings.length > 1) {
            const index = siblings.indexOf(current) + 1;
            selector += `:nth-of-type(${index})`;
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
            .map((item) => textOf(item.innerText || item.textContent))
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
          kind: kindOf(element),
          text,
          label,
          placeholder,
          href,
          selector,
          disabled: !!element.disabled,
          readonly: !!element.readOnly,
        });
        if (result.length >= maxItems) break;
      }

      return result.map((item, index) => ({ index, ...item }));
    }
    """
    return page.evaluate(js, limit)


def page_fingerprint(page: Page, tab_id: str) -> dict[str, Any]:
    return {
        "tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
    }


def update_state(profile_id: str, page: Page, tab_id: str, **extra) -> dict:
    payload = {
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
        "session_health": "running",
        "last_error": None,
    }
    payload.update(extra)
    return write_runtime_state(profile_id, payload)


def load_cached_elements(profile_id: str, page: Page, tab_id: str) -> list[dict[str, Any]]:
    runtime = read_runtime_state(profile_id)
    cached = runtime.get("last_interactive_elements") or []
    fingerprint = runtime.get("last_elements_fingerprint") or {}
    current = page_fingerprint(page, tab_id)
    if (
        fingerprint.get("tab_id") != current["tab_id"]
        or fingerprint.get("url") != current["url"]
        or fingerprint.get("title") != current["title"]
    ):
        raise BrowserControlError(
            "Page changed since last get_interactive_elements call. Refresh the elements list first."
        )
    return cached


def locator_from_target(profile_id: str, page: Page, tab_id: str, args, command: str):
    selectors = [
        bool(getattr(args, "index", None) is not None),
        bool(getattr(args, "selector", None)),
        bool(getattr(args, "label", None)),
        bool(getattr(args, "text", None)),
    ]
    if sum(selectors) != 1:
        raise BrowserControlError(
            f"{command} requires exactly one target selector: --index, --selector, --label, or --text"
        )

    if getattr(args, "index", None) is not None:
        cached = load_cached_elements(profile_id, page, tab_id)
        index = args.index
        if index < 0 or index >= len(cached):
            raise BrowserControlError(f"Interactive element index {index} is out of range")
        selector = cached[index].get("selector")
        if not selector:
            raise BrowserControlError(
                f"Interactive element index {index} has no usable selector hint"
            )
        return page.locator(selector).first

    if getattr(args, "selector", None):
        return page.locator(args.selector).first

    if getattr(args, "label", None):
        label = args.label
        for locator in (
            page.get_by_label(label, exact=True).first,
            page.get_by_placeholder(label, exact=True).first,
        ):
            if locator.count():
                return locator
        raise BrowserControlError(f"No field found by label '{label}'")

    text = args.text
    candidates = [
        page.get_by_role("button", name=text, exact=True).first,
        page.get_by_role("link", name=text, exact=True).first,
        page.get_by_text(text, exact=True).first,
    ]
    for locator in candidates:
        if locator.count():
            return locator
    raise BrowserControlError(f"No element found by text '{text}'")


def ensure_active_page(profile_id: str, context: BrowserContext, runtime: dict) -> tuple[Page, str, list[dict[str, Any]]]:
    page, active_tab, tabs = pick_active_page(profile_id, context, runtime)
    tab_id = active_tab["tab_id"]
    return page, tab_id, tabs


def command_current_state(profile_id: str, context: BrowserContext, runtime: dict) -> dict:
    page, tab_id, tabs = ensure_active_page(profile_id, context, runtime)
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
        "tab_count": len(tabs),
    }


def command_open_url(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout_ms)
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
    }


def command_extract_visible_text(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    text = page.evaluate(
        """
        () => {
          const text = document.body ? document.body.innerText : '';
          return text.replace(/\\s+/g, ' ').trim();
        }
        """
    )
    limited = text[: args.limit]
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
        "text": limited,
        "truncated": len(text) > len(limited),
        "text_length": len(text),
    }


def command_get_interactive_elements(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    elements = interactive_elements(page, args.limit)
    update_state(
        profile_id,
        page,
        tab_id,
        last_interactive_elements=elements,
        last_elements_fingerprint=page_fingerprint(page, tab_id),
    )
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
        "elements": elements,
        "count": len(elements),
    }


def command_click(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    locator = locator_from_target(profile_id, page, tab_id, args, "click")
    locator.wait_for(state="visible", timeout=args.timeout_ms)
    locator.click(timeout=args.timeout_ms)
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
    }


def command_type(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    locator = locator_from_target(profile_id, page, tab_id, args, "type")
    locator.wait_for(state="visible", timeout=args.timeout_ms)
    locator.click(timeout=args.timeout_ms)
    if args.clear:
        locator.clear(timeout=args.timeout_ms)
        locator.type(args.value, timeout=args.timeout_ms)
    else:
        locator.fill(args.value, timeout=args.timeout_ms)
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
    }


def command_press(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    has_target = any(
        getattr(args, attribute, None)
        for attribute in ("selector", "label")
    ) or getattr(args, "index", None) is not None
    if has_target:
        locator = locator_from_target(profile_id, page, tab_id, args, "press")
        locator.wait_for(state="visible", timeout=10000)
        locator.focus()
    page.keyboard.press(args.key)
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
    }


def command_wait_for_text(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    page.wait_for_function(
        """
        (needle) => {
          const text = document.body ? document.body.innerText : '';
          return text.includes(needle);
        }
        """,
        arg=args.text,
        timeout=args.timeout_ms,
    )
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
        "text_found": args.text,
    }


def simple_navigation(profile_id: str, context: BrowserContext, runtime: dict, action: str) -> dict:
    page, tab_id, _tabs = ensure_active_page(profile_id, context, runtime)
    if action == "back":
        page.go_back(wait_until="domcontentloaded")
    elif action == "forward":
        page.go_forward(wait_until="domcontentloaded")
    elif action == "reload":
        page.reload(wait_until="domcontentloaded")
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "url": page.url,
        "title": safe_title(page),
    }


def command_list_tabs(profile_id: str, context: BrowserContext, runtime: dict) -> dict:
    page, tab_id, tabs = ensure_active_page(profile_id, context, runtime)
    update_state(profile_id, page, tab_id)
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": tab_id,
        "tabs": tabs,
    }


def command_switch_tab(profile_id: str, context: BrowserContext, runtime: dict, args) -> dict:
    if args.tab_id is None and args.index is None:
        raise BrowserControlError("switch_tab requires --tab-id or --index")
    pages = list_pages(context)
    tabs = [tab_snapshot(page, index) for index, page in enumerate(pages)]
    chosen_page = None
    chosen_tab = None

    if args.tab_id is not None:
        for page, tab in zip(pages, tabs):
            if tab["tab_id"] == args.tab_id:
                chosen_page = page
                chosen_tab = tab
                break
    elif args.index is not None and 0 <= args.index < len(pages):
        chosen_page = pages[args.index]
        chosen_tab = tabs[args.index]

    if chosen_page is None or chosen_tab is None:
        raise BrowserControlError("Requested tab not found")

    chosen_page.bring_to_front()
    update_state(profile_id, chosen_page, chosen_tab["tab_id"])
    return {
        "ok": True,
        "profile_id": profile_id,
        "active_tab_id": chosen_tab["tab_id"],
        "url": chosen_page.url,
        "title": safe_title(chosen_page),
    }


def execute(profile_id: str, args) -> dict:
    playwright, browser, context, runtime = connect(profile_id)
    try:
        command = args.command
        if command == "current_state":
            return command_current_state(profile_id, context, runtime)
        if command == "open_url":
            return command_open_url(profile_id, context, runtime, args)
        if command == "extract_visible_text":
            return command_extract_visible_text(profile_id, context, runtime, args)
        if command == "get_interactive_elements":
            return command_get_interactive_elements(profile_id, context, runtime, args)
        if command == "click":
            return command_click(profile_id, context, runtime, args)
        if command == "type":
            return command_type(profile_id, context, runtime, args)
        if command == "press":
            return command_press(profile_id, context, runtime, args)
        if command == "wait_for_text":
            return command_wait_for_text(profile_id, context, runtime, args)
        if command in {"back", "forward", "reload"}:
            return simple_navigation(profile_id, context, runtime, command)
        if command == "list_tabs":
            return command_list_tabs(profile_id, context, runtime)
        if command == "switch_tab":
            return command_switch_tab(profile_id, context, runtime, args)
        raise BrowserControlError(f"Unsupported command: {command}")
    finally:
        disconnect(playwright, browser)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = execute(args.profile_id, args)
        return json_print(payload, exit_code=0)
    except TimeoutError as exc:
        write_runtime_state(
            args.profile_id,
            {
                "last_error": f"Timeout: {exc}",
            },
        )
        return json_print(
            {
                "ok": False,
                "error": "timeout",
                "message": str(exc),
            },
            exit_code=1,
        )
    except (BrowserControlError, Error) as exc:
        write_runtime_state(
            args.profile_id,
            {
                "last_error": str(exc),
            },
        )
        return json_print(
            {
                "ok": False,
                "error": "browser_control_error",
                "message": str(exc),
            },
            exit_code=1,
        )
    except Exception as exc:
        write_runtime_state(
            args.profile_id,
            {
                "last_error": f"Unexpected error: {exc}",
            },
        )
        return json_print(
            {
                "ok": False,
                "error": "unexpected_error",
                "message": str(exc),
            },
            exit_code=1,
        )

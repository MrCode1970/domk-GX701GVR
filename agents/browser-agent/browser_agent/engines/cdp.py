"""Thin synchronous CDP client over websockets."""

import json
import threading
from typing import Any

import websocket

from browser_agent.common import cdp_probe, fetch_json


class CDPError(RuntimeError):
    pass


class CDPSession:
    """Single CDP session connected to one target (page or browser)."""

    def __init__(self, ws_url: str):
        self._ws = websocket.create_connection(ws_url, timeout=10)
        self._id = 0
        self._lock = threading.Lock()

    def send(self, method: str, params: dict | None = None) -> dict:
        with self._lock:
            self._id += 1
            msg_id = self._id

        message = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        self._ws.send(json.dumps(message))

        # Read responses until we get ours (skip events)
        while True:
            raw = self._ws.recv()
            response = json.loads(raw)
            if response.get("id") == msg_id:
                if "error" in response:
                    err = response["error"]
                    raise CDPError(f"CDP {method}: {err.get('message', err)}")
                return response.get("result", {})
            # else: it's an event, skip

    def evaluate(self, expression: str) -> Any:
        result = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        exception = result.get("exceptionDetails")
        if exception:
            text = exception.get("text", "")
            ex_obj = exception.get("exception", {})
            desc = ex_obj.get("description", ex_obj.get("value", ""))
            raise CDPError(f"JS error: {text} {desc}".strip())
        return result.get("result", {}).get("value")

    def call_function(self, function_declaration: str, args: list | None = None) -> Any:
        call_args = []
        if args:
            for arg in args:
                call_args.append({"value": arg})

        result = self.send("Runtime.evaluate", {
            "expression": f"({function_declaration})({', '.join(json.dumps(a) for a in (args or []))})",
            "returnByValue": True,
            "awaitPromise": True,
        })
        exception = result.get("exceptionDetails")
        if exception:
            text = exception.get("text", "")
            ex_obj = exception.get("exception", {})
            desc = ex_obj.get("description", ex_obj.get("value", ""))
            raise CDPError(f"JS error: {text} {desc}".strip())
        return result.get("result", {}).get("value")

    def navigate(self, url: str) -> dict:
        return self.send("Page.navigate", {"url": url})

    def reload(self) -> dict:
        return self.send("Page.reload")

    def get_url(self) -> str:
        return self.evaluate("location.href")

    def get_title(self) -> str:
        return self.evaluate("document.title")

    def insert_text(self, text: str) -> None:
        self.send("Input.insertText", {"text": text})

    def dispatch_key(self, key: str) -> None:
        info = KEY_MAP.get(key, {"key": key, "code": f"Key{key.upper()}", "text": key})
        self.send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": info["key"],
            "code": info["code"],
            **( {"text": info["text"]} if "text" in info else {}),
        })
        self.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": info["key"],
            "code": info["code"],
        })

    def wait_for(self, js_expression: str, timeout_ms: int = 15000) -> bool:
        import time
        deadline = time.monotonic() + (timeout_ms / 1000)
        while time.monotonic() < deadline:
            try:
                if self.evaluate(js_expression):
                    return True
            except CDPError:
                pass
            time.sleep(0.25)
        raise CDPError(f"Timeout waiting for condition after {timeout_ms}ms")

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


KEY_MAP = {
    "Enter":     {"key": "Enter",     "code": "Enter",      "text": "\r"},
    "Tab":       {"key": "Tab",       "code": "Tab",        "text": "\t"},
    "Escape":    {"key": "Escape",    "code": "Escape"},
    "Backspace": {"key": "Backspace", "code": "Backspace"},
    "Delete":    {"key": "Delete",    "code": "Delete"},
    "ArrowUp":   {"key": "ArrowUp",   "code": "ArrowUp"},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown"},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft"},
    "ArrowRight":{"key": "ArrowRight","code": "ArrowRight"},
    "Home":      {"key": "Home",      "code": "Home"},
    "End":       {"key": "End",       "code": "End"},
    "PageUp":    {"key": "PageUp",    "code": "PageUp"},
    "PageDown":  {"key": "PageDown",  "code": "PageDown"},
    " ":         {"key": " ",         "code": "Space",      "text": " "},
    "Space":     {"key": " ",         "code": "Space",      "text": " "},
}


class CDPBrowser:
    """Manages connections to a Chrome instance via CDP."""

    def __init__(self, port: int):
        self.port = port
        self._browser_session: CDPSession | None = None
        self._page_sessions: dict[str, CDPSession] = {}

    def connect(self) -> dict:
        info = cdp_probe(self.port)
        if info is None:
            raise CDPError(f"CDP not available on port {self.port}")
        self._browser_session = CDPSession(info["web_socket_debugger_url"])
        return info

    def list_targets(self) -> list[dict]:
        targets = fetch_json(f"http://127.0.0.1:{self.port}/json/list")
        if not isinstance(targets, list):
            raise CDPError("Failed to list targets")
        return [t for t in targets if t.get("type") == "page"]

    def page_session(self, target_id: str | None = None) -> CDPSession:
        """Get or create a CDP session for a specific page target."""
        if target_id and target_id in self._page_sessions:
            return self._page_sessions[target_id]

        targets = self.list_targets()
        if not targets:
            raise CDPError("No page targets available")

        if target_id:
            target = next((t for t in targets if t["id"] == target_id), None)
            if not target:
                raise CDPError(f"Target {target_id} not found")
        else:
            target = targets[0]
            target_id = target["id"]

        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            raise CDPError(f"No websocket URL for target {target_id}")

        session = CDPSession(ws_url)
        self._page_sessions[target_id] = session
        return session

    def activate_target(self, target_id: str) -> None:
        fetch_json(f"http://127.0.0.1:{self.port}/json/activate/{target_id}")

    def close(self) -> None:
        for session in self._page_sessions.values():
            session.close()
        self._page_sessions.clear()
        if self._browser_session:
            self._browser_session.close()
            self._browser_session = None

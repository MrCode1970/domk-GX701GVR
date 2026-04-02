import json
import socket
import shutil
import urllib.error
import urllib.request
from datetime import datetime, UTC
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "profiles.json"
PROFILES_DIR = BASE / "profiles"
RUNTIME_DIR = BASE / "runtime"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def runtime_state_path(profile_id: str) -> Path:
    ensure_runtime_dir()
    return RUNTIME_DIR / f"{profile_id}.json"


def load_profiles() -> dict[str, dict]:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    profiles = data.get("profiles", [])
    return {profile["id"]: profile for profile in profiles}


def profile_order() -> list[str]:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    return [profile["id"] for profile in data.get("profiles", [])]


def get_profile(profile_id: str) -> dict:
    profiles = load_profiles()
    profile = profiles.get(profile_id)
    if not profile:
        raise KeyError(f"Unknown profile: {profile_id}")
    return profile


def profile_control_port(profile_id: str, profile: dict | None = None) -> int:
    if profile is None:
        profile = get_profile(profile_id)

    explicit = profile.get("controlPort")
    if explicit:
        return int(explicit)

    ordered_ids = profile_order()
    try:
        index = ordered_ids.index(profile_id)
    except ValueError:
        index = 0
    return 9333 + index


def profile_user_data_dir(profile_id: str) -> Path:
    return PROFILES_DIR / profile_id


def pick_browser_executable() -> str | None:
    candidates = [
        shutil.which("google-chrome-stable"),
        shutil.which("google-chrome"),
        shutil.which("chromium-browser"),
        shutil.which("chromium"),
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def read_runtime_state(profile_id: str) -> dict:
    path = runtime_state_path(profile_id)
    if not path.exists():
        return {
            "profile_id": profile_id,
            "session_health": "not_started",
            "last_error": None,
            "last_interactive_elements": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_runtime_state(profile_id: str, state: dict) -> dict:
    path = runtime_state_path(profile_id)
    current = read_runtime_state(profile_id)
    current.update(state)
    current["profile_id"] = profile_id
    current["updated_at"] = utc_now()
    path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return current


def cdp_base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def fetch_json(url: str, timeout: float = 1.0) -> dict | list | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def cdp_probe(port: int, timeout: float = 1.0) -> dict | None:
    base_url = cdp_base_url(port)
    version = fetch_json(f"{base_url}/json/version", timeout=timeout)
    targets = fetch_json(f"{base_url}/json/list", timeout=timeout)
    if not isinstance(version, dict) or not isinstance(targets, list):
        return None
    web_socket = version.get("webSocketDebuggerUrl")
    if not web_socket:
        return None
    return {
        "base_url": base_url,
        "web_socket_debugger_url": web_socket,
        "browser": version.get("Browser"),
        "protocol_version": version.get("Protocol-Version"),
        "target_count": len(targets),
    }


def is_tcp_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return True
    return False

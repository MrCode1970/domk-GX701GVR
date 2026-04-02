import argparse
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from browser_agent.common import (
    cdp_probe,
    get_profile,
    is_tcp_port_in_use,
    pick_browser_executable,
    profile_control_port,
    profile_user_data_dir,
    write_runtime_state,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch a persistent Chromium profile for browser-agent."
    )
    parser.add_argument("profile_id", help="Profile id from config/profiles.json")
    parser.add_argument(
        "--start-url",
        dest="start_url",
        help="Override the profile start URL for this launch",
    )
    parser.add_argument(
        "--control-port",
        dest="control_port",
        type=int,
        help="CDP port for browser control connections",
    )
    parser.add_argument(
        "--hold-ms",
        dest="hold_ms",
        type=int,
        default=600000,
        help="How long to keep the launcher process alive while the browser is open",
    )
    parser.add_argument(
        "--cdp-ready-timeout-ms",
        dest="cdp_ready_timeout_ms",
        type=int,
        default=15000,
        help="How long to wait for the CDP HTTP endpoint to become reachable",
    )
    return parser


def wait_for_cdp_ready(port: int, timeout_ms: int) -> dict | None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        probe = cdp_probe(port, timeout=1.0)
        if probe is not None:
            return probe
        time.sleep(0.25)
    return None


def wait_until_stopped(context, timeout_ms: int = 1500) -> None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        try:
            if not context.browser.is_connected():
                return
        except Exception:
            return
        time.sleep(0.1)


def monitor_browser_lifecycle(context, hold_ms: int) -> str:
    deadline = time.monotonic() + (hold_ms / 1000)
    while time.monotonic() < deadline:
        try:
            if not context.browser.is_connected():
                return "disconnected"
            open_pages = [page for page in context.pages if not page.is_closed()]
            if not open_pages:
                return "disconnected"
        except Exception:
            return "disconnected"
        time.sleep(0.5)
    return "timeout"


def launch_profile(args: argparse.Namespace) -> int:
    profile = get_profile(args.profile_id)
    user_data_dir = profile_user_data_dir(args.profile_id)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    start_url = args.start_url or profile.get("startUrl", "https://www.google.com")
    executable_path = pick_browser_executable()
    control_port = args.control_port or profile_control_port(args.profile_id, profile)

    launch_args = [
        "--start-maximized",
        "--disable-infobars",
        "--no-first-run",
        "--no-default-browser-check",
        f"--remote-debugging-port={control_port}",
        "--remote-allow-origins=*",
    ]

    print(f"🚀 Launching profile: {args.profile_id}")
    print(f"📁 User data dir: {user_data_dir}")
    print(f"🔗 Start URL: {start_url}")
    print(f"🌐 Executable: {executable_path or 'Playwright bundled Chromium'}")
    print(f"🧠 Control port: {control_port}")

    if is_tcp_port_in_use(control_port):
        message = (
            f"Control port {control_port} is already in use; refusing to launch with a conflicting CDP port"
        )
        write_runtime_state(
            args.profile_id,
            {
                "control_port": control_port,
                "launcher_pid": os.getpid(),
                "session_health": "error",
                "last_error": message,
            },
        )
        print(f"❌ Launch failed: {message}")
        return 1

    write_runtime_state(
        args.profile_id,
        {
            "profile_id": args.profile_id,
            "control_port": control_port,
            "launcher_pid": os.getpid(),
            "session_health": "starting",
            "last_error": None,
            "cdp_ready": False,
            "cdp_endpoint": None,
        },
    )

    with sync_playwright() as playwright:
        kwargs = dict(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=launch_args,
            ignore_default_args=["--enable-automation"],
            no_viewport=True,
            chromium_sandbox=True,
        )
        if executable_path:
            kwargs["executable_path"] = executable_path

        context = None
        try:
            context = playwright.chromium.launch_persistent_context(**kwargs)
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """
            )
            page.goto(start_url, wait_until="domcontentloaded")

            cdp_info = wait_for_cdp_ready(control_port, args.cdp_ready_timeout_ms)
            if cdp_info is None:
                message = (
                    f"CDP endpoint did not become ready on port {control_port} within "
                    f"{args.cdp_ready_timeout_ms} ms"
                )
                write_runtime_state(
                    args.profile_id,
                    {
                        "url": page.url,
                        "title": page.title(),
                        "session_health": "error",
                        "last_error": message,
                        "cdp_ready": False,
                        "cdp_endpoint": None,
                    },
                )
                print(f"❌ Launch failed: {message}")
                return 1

            write_runtime_state(
                args.profile_id,
                {
                    "active_tab_id": None,
                    "url": page.url,
                    "title": page.title(),
                    "session_health": "running",
                    "last_error": None,
                    "cdp_ready": True,
                    "cdp_endpoint": cdp_info["base_url"],
                    "cdp_web_socket_debugger_url": cdp_info["web_socket_debugger_url"],
                },
            )

            print("✅ Browser opened with persistent profile")
            print(f"🔌 CDP ready: {cdp_info['base_url']}")
            print(
                "💡 Close the browser window when finished; session data stays in profile folder"
            )
            lifecycle_result = monitor_browser_lifecycle(context, args.hold_ms)
            if lifecycle_result == "disconnected":
                write_runtime_state(
                    args.profile_id,
                    {
                        "session_health": "disconnected",
                        "last_error": "Browser window was closed by user",
                        "cdp_ready": False,
                    },
                )
                print("ℹ️ Browser window was closed by user")
                return 0

            write_runtime_state(
                args.profile_id,
                {
                    "session_health": "stopping",
                    "last_error": None,
                },
            )
            print("ℹ️ Launcher hold timeout reached; closing browser")
            return 0
        except KeyboardInterrupt:
            write_runtime_state(
                args.profile_id,
                {
                    "session_health": "stopping",
                    "last_error": "Launcher interrupted by user",
                    "cdp_ready": False,
                },
            )
            return 130
        except Exception as exc:
            write_runtime_state(
                args.profile_id,
                {
                    "session_health": "error",
                    "last_error": str(exc),
                    "cdp_ready": False,
                },
            )
            print(f"❌ Launch failed: {exc}")
            return 1
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
                wait_until_stopped(context)
                runtime = write_runtime_state(args.profile_id, {})
                if runtime.get("session_health") != "error":
                    write_runtime_state(
                        args.profile_id,
                        {
                            "session_health": "stopped"
                            if runtime.get("session_health") != "disconnected"
                            else "disconnected",
                            "cdp_ready": False,
                        },
                    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return launch_profile(args)

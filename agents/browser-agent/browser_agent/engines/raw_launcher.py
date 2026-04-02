"""M1 prototype: launch Chrome via subprocess with minimal flags, prove CDP ready."""

import os
import signal
import subprocess
import sys
import time

# Allow running as standalone script or as module
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))

from browser_agent.common import cdp_probe, pick_browser_executable, profile_user_data_dir


def launch(
    profile_id: str,
    control_port: int = 9335,
    start_url: str = "https://www.google.com",
    hold_seconds: int = 120,
    cdp_timeout: int = 15,
    detach: bool = False,
) -> int:
    executable = pick_browser_executable()
    if not executable:
        print("No Chrome/Chromium found")
        return 1

    user_data_dir = profile_user_data_dir(profile_id)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    args = [
        executable,
        f"--user-data-dir={user_data_dir}",
        f"--remote-debugging-port={control_port}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-infobars",
        start_url,
    ]

    print(f"Launching: {executable}")
    print(f"Profile:   {user_data_dir}")
    print(f"CDP port:  {control_port}")
    print(f"Args:      {' '.join(args[1:])}")

    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )

    print(f"PID:       {process.pid}")
    print(f"Waiting for CDP on port {control_port}...")

    # Wait for CDP ready
    deadline = time.monotonic() + cdp_timeout
    cdp_info = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(f"Chrome exited early with code {process.returncode}")
            return 1
        cdp_info = cdp_probe(control_port, timeout=1.0)
        if cdp_info is not None:
            break
        time.sleep(0.25)

    if cdp_info is None:
        print(f"CDP not ready after {cdp_timeout}s — killing")
        process.terminate()
        process.wait(timeout=5)
        return 1

    print(f"CDP ready: {cdp_info['base_url']}")
    print(f"Browser:   {cdp_info['browser']}")
    print(f"Targets:   {cdp_info['target_count']}")
    print(f"WebSocket: {cdp_info['web_socket_debugger_url']}")

    if detach:
        print(f"\nDetached. Chrome PID {process.pid} running independently.")
        print("Close the browser window manually when done.")
        return 0

    print(f"\nHolding for {hold_seconds}s. Ctrl+C or close browser to stop.")

    # Hold and monitor
    try:
        deadline = time.monotonic() + hold_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                print("Browser closed by user")
                return 0
            time.sleep(0.5)
        print("Hold timeout — terminating")
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="M1: raw Chrome launcher prototype")
    parser.add_argument("profile_id", nargs="?", default="test")
    parser.add_argument("--port", type=int, default=9335)
    parser.add_argument("--url", default="https://www.google.com")
    parser.add_argument("--hold", type=int, default=120)
    parser.add_argument("--detach", action="store_true", help="Exit after CDP ready, leave Chrome running")
    args = parser.parse_args()

    raise SystemExit(launch(args.profile_id, args.port, args.url, args.hold, detach=args.detach))

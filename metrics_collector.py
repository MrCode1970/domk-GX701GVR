#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "monitor"
DATA_DIR.mkdir(exist_ok=True)
METRICS_PATH = DATA_DIR / "metrics.json"
HISTORY_PATH = DATA_DIR / "history.json"
PORT = int(os.environ.get("OPENCLAW_MONITOR_PORT", "8765"))
INTERVAL = float(os.environ.get("OPENCLAW_MONITOR_INTERVAL", "3"))
MAX_POINTS = int(os.environ.get("OPENCLAW_MONITOR_MAX_POINTS", "240"))

PROC_MATCHERS = {
    "openclaw_gateway": ["openclaw-gateway"],
    "python_stt": ["transcribe-audio.py", "faster_whisper", "faster-whisper"],
    "edge_tts": ["edge-tts"],
    "node_llama": ["node-llama-cpp", "embeddinggemma", "llama"],
}

state = {
    "cpu_prev": None,
    "cpu_prev_total": None,
    "proc_prev": {},
}


def read_proc_stat():
    with open("/proc/stat", "r", encoding="utf-8") as f:
        first = f.readline().strip().split()
    values = list(map(int, first[1:]))
    idle = values[3] + values[4]
    total = sum(values)
    return idle, total


def get_cpu_percent():
    idle, total = read_proc_stat()
    prev_idle = state["cpu_prev"]
    prev_total = state["cpu_prev_total"]
    state["cpu_prev"] = idle
    state["cpu_prev_total"] = total
    if prev_idle is None or prev_total is None:
        return None
    idle_delta = idle - prev_idle
    total_delta = total - prev_total
    if total_delta <= 0:
        return 0.0
    return round(100.0 * (1.0 - idle_delta / total_delta), 2)


def get_mem_info():
    data = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            key, value = line.split(":", 1)
            data[key] = int(value.strip().split()[0]) * 1024
    total = data.get("MemTotal", 0)
    available = data.get("MemAvailable", 0)
    used = max(total - available, 0)
    percent = round((used / total) * 100, 2) if total else 0.0
    return {
        "total": total,
        "used": used,
        "available": available,
        "percent": percent,
    }


def get_disk_info(path="/home/domk/.openclaw"):
    usage = shutil.disk_usage(path)
    used = usage.total - usage.free
    percent = round((used / usage.total) * 100, 2) if usage.total else 0.0
    return {
        "path": path,
        "total": usage.total,
        "used": used,
        "free": usage.free,
        "percent": percent,
    }


def get_loadavg():
    try:
        a, b, c = os.getloadavg()
        return {"1m": round(a, 2), "5m": round(b, 2), "15m": round(c, 2)}
    except OSError:
        return {"1m": 0.0, "5m": 0.0, "15m": 0.0}


def get_gpu_info():
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace").strip()
    except Exception:
        return None
    if not out:
        return None
    first = out.splitlines()[0]
    parts = [p.strip() for p in first.split(",")]
    if len(parts) < 7:
        return None
    name, gpu_util, mem_util, mem_used, mem_total, temp, power = parts[:7]
    try:
        return {
            "name": name,
            "utilization_gpu": round(float(gpu_util), 2),
            "utilization_memory": round(float(mem_util), 2),
            "memory_used_mb": round(float(mem_used), 2),
            "memory_total_mb": round(float(mem_total), 2),
            "temperature_c": round(float(temp), 2),
            "power_w": round(float(power), 2),
        }
    except ValueError:
        return None


def parse_ps():
    cmd = [
        "ps",
        "-eo",
        "pid=,ppid=,pcpu=,pmem=,rss=,comm=,args=",
    ]
    out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(None, 6)
        if len(parts) < 7:
            continue
        pid, ppid, pcpu, pmem, rss, comm, args = parts
        rows.append(
            {
                "pid": int(pid),
                "ppid": int(ppid),
                "pcpu": float(pcpu.replace(",", ".")),
                "pmem": float(pmem.replace(",", ".")),
                "rss_kb": int(rss),
                "comm": comm,
                "args": args,
            }
        )
    return rows


def aggregate_processes(rows):
    groups = {}
    for key, needles in PROC_MATCHERS.items():
        matched = []
        for row in rows:
            hay = f"{row['comm']} {row['args']}".lower()
            if any(n.lower() in hay for n in needles):
                matched.append(row)
        groups[key] = {
            "count": len(matched),
            "cpu_percent": round(sum(r["pcpu"] for r in matched), 2),
            "mem_percent": round(sum(r["pmem"] for r in matched), 2),
            "rss_mb": round(sum(r["rss_kb"] for r in matched) / 1024, 2),
            "pids": [r["pid"] for r in matched][:10],
        }
    top_cpu = sorted(rows, key=lambda r: r["pcpu"], reverse=True)[:8]
    top_mem = sorted(rows, key=lambda r: r["rss_kb"], reverse=True)[:8]
    return groups, top_cpu, top_mem


def dir_size(path):
    total = 0
    p = Path(path)
    if not p.exists():
        return 0
    for root, _, files in os.walk(p):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def collect_once():
    rows = parse_ps()
    proc_groups, top_cpu, top_mem = aggregate_processes(rows)
    snapshot = {
        "timestamp": int(time.time()),
        "cpu": {"percent": get_cpu_percent()},
        "memory": get_mem_info(),
        "disk": get_disk_info(),
        "gpu": get_gpu_info(),
        "loadavg": get_loadavg(),
        "process_groups": proc_groups,
        "top_cpu": top_cpu,
        "top_mem": top_mem,
        "sizes": {
            "openclaw_cache": dir_size("/home/domk/.openclaw/cache"),
            "openclaw_memory": dir_size("/home/domk/.openclaw/memory"),
            "audio_stt_venv": dir_size("/home/domk/.openclaw/venvs/audio-stt"),
        },
    }
    return snapshot


def load_history():
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def collector_loop():
    history = load_history()
    while True:
        snapshot = collect_once()
        history.append(snapshot)
        history = history[-MAX_POINTS:]
        save_json(METRICS_PATH, snapshot)
        save_json(HISTORY_PATH, history)
        time.sleep(INTERVAL)


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def log_message(self, fmt, *args):
        return


def serve():
    os.chdir(DATA_DIR)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), NoCacheHandler)
    print(f"Monitor dashboard: http://127.0.0.1:{PORT}/dashboard.html")
    server.serve_forever()


if __name__ == "__main__":
    t = threading.Thread(target=collector_loop, daemon=True)
    t.start()
    serve()

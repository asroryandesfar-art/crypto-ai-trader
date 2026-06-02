"""Start/stop local backend and dashboard by PID file.

This avoids broad process kills and keeps logs/PIDs under runtime/.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
LOGS = ROOT / "logs"
RUNTIME = ROOT / "runtime"


def ensure_dirs() -> None:
    LOGS.mkdir(exist_ok=True)
    RUNTIME.mkdir(exist_ok=True)


def pid_file(name: str) -> Path:
    return RUNTIME / f"{name}.pid"


def read_pid(name: str) -> int | None:
    try:
        return int(pid_file(name).read_text(encoding="utf-8").strip())
    except Exception:
        return None


def is_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop(name: str) -> None:
    pid = read_pid(name)
    if not is_running(pid):
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.time() + 8
    while time.time() < deadline:
        if not is_running(pid):
            return
        time.sleep(0.25)
        os.kill(pid, signal.SIGKILL)


def stop_project_processes() -> None:
    """Best-effort cleanup for orphaned local project backend/dashboard processes."""
    if os.name != "nt":
        stop("backend")
        stop("dashboard")
        return
    ps = (
        "$root = '"
        + str(ROOT).replace("'", "''")
        + "'; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like \"*$root*\" -and "
        "($_.CommandLine -like '* main.py*' -or $_.CommandLine -like '*crypto_dashboard.py*') } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch(name: str, args: list[str]) -> int:
    ensure_dirs()
    if is_running(read_pid(name)):
        return read_pid(name) or 0

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW

    out = open(LOGS / f"{name}.out.log", "a", encoding="utf-8")
    err = open(LOGS / f"{name}.err.log", "a", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PYTHON), *args],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=out,
        stderr=err,
        creationflags=creationflags,
        close_fds=False,
    )
    pid_file(name).write_text(str(proc.pid), encoding="utf-8")
    return proc.pid


def start() -> None:
    if not PYTHON.exists():
        raise SystemExit(f"Missing virtualenv Python: {PYTHON}")
    stop_project_processes()
    time.sleep(1)
    backend_pid = launch("backend", ["main.py"])
    dashboard_pid = launch(
        "dashboard",
        [
            "-m",
            "streamlit",
            "run",
            "crypto_dashboard.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            "8501",
            "--server.headless",
            "true",
        ],
    )
    print(f"backend_pid={backend_pid}")
    print(f"dashboard_pid={dashboard_pid}")
    print("dashboard_url=http://127.0.0.1:8501")


def status() -> None:
    for name in ("backend", "dashboard"):
        pid = read_pid(name)
        print(f"{name}: pid={pid or '-'} running={is_running(pid)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start", "stop", "restart", "status"))
    args = parser.parse_args()
    if args.command in {"stop", "restart"}:
        stop_project_processes()
    if args.command in {"start", "restart"}:
        start()
    if args.command == "status":
        status()
    return 0


if __name__ == "__main__":
    sys.exit(main())

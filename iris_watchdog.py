"""
IRIS Background Persistent Supervisor / Watchdog
Keeps IRIS running permanently 24/7 in the background without a console window.
Automatically restarts IRIS if it ever encounters an unhandled exception or terminates unexpectedly.
Ensures single-instance execution to prevent duplicate floating orbs.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import psutil

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = Path(sys.executable)
PYTHONW = PYTHON_EXE.parent / "pythonw.exe"
RUNNER_EXE = str(PYTHONW) if PYTHONW.exists() else str(PYTHON_EXE)

LOG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "IRIS_Assistant" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
WATCHDOG_LOG = LOG_DIR / "iris_watchdog.log"


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [WATCHDOG] {msg}\n"
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def is_iris_already_running() -> bool:
    """Checks if another IRIS assistant process is already active."""
    current_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["pid"] == current_pid:
                continue
            cmdline = proc.info.get("cmdline") or []
            cmd_str = " ".join(cmdline).lower()
            if "iris.main" in cmd_str:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def run_supervisor():
    log("==========================================")
    log("Starting IRIS Persistent Watchdog Loop")
    log(f"Runner executable: {RUNNER_EXE}")
    log(f"Base directory: {BASE_DIR}")
    log("==========================================")

    while True:
        if is_iris_already_running():
            log("An active IRIS instance is already running. Monitoring...")
            time.sleep(5)
            continue

        log("Launching IRIS assistant process...")
        try:
            # CREATE_NO_WINDOW = 0x08000000 on Windows
            creation_flags = 0x08000000 if os.name == "nt" else 0
            proc = subprocess.Popen(
                [RUNNER_EXE, "-m", "iris.main"],
                cwd=str(BASE_DIR),
                creationflags=creation_flags
            )
            log(f"IRIS process started with PID {proc.pid}")
            
            exit_code = proc.wait()
            log(f"IRIS process exited with code {exit_code}")

            # Check if stop was explicitly requested via stop_iris.bat (flag file)
            stop_flag = BASE_DIR / ".stop_iris"
            if stop_flag.exists():
                log("Explicit stop flag detected. Watchdog stopping.")
                try:
                    stop_flag.unlink()
                except Exception:
                    pass
                break

            # Always auto-restart IRIS 24/7 so it runs all the time without interruption
            log(f"IRIS process terminated (Code {exit_code}). Auto-restarting in 2 seconds to keep it on all time...")
            time.sleep(2)

        except Exception as e:
            log(f"Error in supervisor loop: {e}. Retrying in 3 seconds...")
            time.sleep(3)


if __name__ == "__main__":
    run_supervisor()

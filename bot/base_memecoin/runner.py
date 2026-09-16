#!/usr/bin/env python3
"""
Base chain bot runner - ticks every 60 seconds
"""
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime, timezone

BOT_PATH = "/opt/data/hermes_work/bot/base_memecoin/base_bot.py"
LOG_PATH = "/opt/data/hermes_work/bot/base_memecoin/logs/runner.log"
INTERVAL_SECONDS = 60

def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] [runner] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


import os, sys
LOCK_FILE = "/tmp/base_bot_runner.lock"

def is_already_running():
    if os.path.exists(LOCK_FILE):
        try:
            pid = int(open(LOCK_FILE).read().strip())
            os.kill(pid, 0)
            # PID exists - check if it's actually a runner
            cmdline_path = f"/proc/{pid}/cmdline"
            if os.path.exists(cmdline_path):
                cmdline = open(cmdline_path).read()
                if "base_memecoin/runner" in cmdline:
                    return True
                else:
                    # PID reused by another process - take over lock
                    pass
            else:
                return True
        except (OSError, ValueError):
            pass
    # Write our PID to lock
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return False

def main():
    if is_already_running():
        log("ERROR: Another base bot runner is already running. Exiting.")
        sys.exit(1)
    log(f"Starting base bot runner (interval={INTERVAL_SECONDS}s) PID={os.getpid()}")
    while True:
        try:
            log("Tick")
            result = subprocess.run(
                ['/opt/data/hermes_work/.venv/bin/python', BOT_PATH],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                log(f"Tick OK")
                # Show last line of output
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        log(f"Last: {lines[-1][:120]}")
            else:
                log(f"Tick FAILED (rc={result.returncode})")
                if result.stderr:
                    log(f"STDERR: {result.stderr[:500]}")
        except Exception as e:
            log(f"Tick ERROR: {e}")

        log(f"Sleeping {INTERVAL_SECONDS}s")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

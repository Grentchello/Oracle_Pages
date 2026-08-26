#!/usr/bin/env python3
"""Bot runner — ticks every 5 min. Same as before, just runs bot.py."""
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
INTERVAL_SECONDS = 300


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [runner] {msg}", flush=True)


def main():
    log(f"Starting bot runner (interval={INTERVAL_SECONDS}s)")
    while True:
        log("Tick")
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "bot.py")],
            cwd=str(SCRIPT_DIR.parent),
            timeout=180,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log(f"Tick OK\n{result.stdout[-500:]}")
        else:
            log(f"Tick FAILED (rc={result.returncode})\nSTDOUT: {result.stdout[-300:]}\nSTDERR: {result.stderr[-300:]}")
        log(f"Sleeping {INTERVAL_SECONDS}s")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
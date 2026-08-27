#!/usr/bin/env python3
"""Bot runner for trading pairs bot. Ticks every 60s."""
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
INTERVAL_SECONDS = 60


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [pairs-runner] {msg}", flush=True)


def main():
    log(f"Starting trading pairs bot runner (interval={INTERVAL_SECONDS}s)")
    py = sys.executable
    bot_script = str(SCRIPT_DIR / "trading_pairs_bot.py")
    workdir = str(SCRIPT_DIR.parent)
    while True:
        log("Tick")
        result = subprocess.run(
            [py, bot_script],
            cwd=workdir,
            timeout=60,
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

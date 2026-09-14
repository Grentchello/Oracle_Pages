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


def main():
    log(f"Starting base bot runner (interval={INTERVAL_SECONDS}s)")
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

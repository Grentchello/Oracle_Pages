#!/usr/bin/env python3
"""
Memecoin bot runner — keeps the bot ticking every 5 minutes.
Run in background: `python3 bot/runner.py` and it'll loop forever.
"""
import subprocess
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
BOT_SCRIPT = SCRIPT_DIR / "bot.py"
INTERVAL_SECONDS = 300  # 5 minutes


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [runner] {msg}", flush=True)


def run_bot():
    log(f"Tick: running {BOT_SCRIPT}")
    try:
        result = subprocess.run(
            [sys.executable, str(BOT_SCRIPT)],
            cwd=str(SCRIPT_DIR.parent),
            timeout=120,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log(f"Tick OK\n{result.stdout}")
        else:
            log(f"Tick FAILED (exit {result.returncode})\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
    except subprocess.TimeoutExpired:
        log("Tick TIMED OUT after 120s")
    except Exception as e:
        log(f"Tick ERROR: {e}")


def main():
    log(f"Starting bot runner (interval={INTERVAL_SECONDS}s)")
    # Run immediately, then on a fixed schedule
    while True:
        run_bot()
        log(f"Sleeping {INTERVAL_SECONDS}s until next tick")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
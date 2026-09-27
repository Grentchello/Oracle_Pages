#!/usr/bin/env python3
"""
Copy-trading supervisor - monitors webhook server + tunnel + Helius webhook.
Runs as a daemon. Checks every 60 seconds.
"""
import os
import sys
import time
import signal
import json
import subprocess
import urllib.request
from pathlib import Path

LOGS = Path("/opt/data/hermes_work/bot/copy_trading/logs")
LOGS.mkdir(parents=True, exist_ok=True)
SUP_LOG = LOGS / "supervisor.log"

WEB_PORT = 8765
WEB_DIR = Path("/opt/data/hermes_work/bot/copy_trader")
WEB_SCRIPT = WEB_DIR / "webhook_server.py"
WEB_VENV = Path("/opt/data/hermes_work/.venv/bin/python")
WEB_LOG = LOGS / "webhook.log"
WEB_PID_FILE = LOGS / "webhook.pid"

CF_BIN = Path("/opt/data/home/.local/bin/cloudflared")
CF_LOG = Path("/tmp/cloudflared.log")
CF_PID_FILE = LOGS / "cf.pid"
CF_URL_FILE = LOGS / "tunnel_url.txt"

HEL_KEY = "03b2d88f-daf1-4cdd-bbb1-a30351b0247a"
CFG = WEB_DIR / "cache" / "helius_webhook.json"

CHECK_INTERVAL = 60  # seconds


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {msg}"
    with open(SUP_LOG, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def is_pid_alive(pid_file):
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except:
        return False


def webhook_healthy():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{WEB_PORT}/health", timeout=3) as r:
            return r.status == 200
    except:
        return False


def start_webhook():
    log("Starting webhook server...")
    # Kill any existing
    if WEB_PID_FILE.exists():
        try:
            pid = int(WEB_PID_FILE.read_text().strip())
            os.kill(pid, 9)
        except:
            pass
    
    # Start new
    proc = subprocess.Popen(
        [str(WEB_VENV), "-u", str(WEB_SCRIPT)],
        cwd=str(WEB_DIR),
        stdout=open(WEB_LOG, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    WEB_PID_FILE.write_text(str(proc.pid))
    time.sleep(4)
    if webhook_healthy():
        log(f"✅ Webhook up (PID {proc.pid})")
    else:
        log("❌ Webhook failed health check")


def tunnel_alive():
    # Just check if PID is alive. URL health check from inside container
    # is unreliable (DNS may not resolve trycloudflare.com from internal network)
    return is_pid_alive(CF_PID_FILE)


def get_tunnel_url():
    if CF_URL_FILE.exists():
        url = CF_URL_FILE.read_text().strip()
        if url:
            return url
    if CF_LOG.exists():
        import re
        m = re.search(r"https://[a-z-]+\.trycloudflare\.com", CF_LOG.read_text())
        if m:
            return m.group(0)
    return None


def start_tunnel():
    log("Starting tunnel...")
    if CF_PID_FILE.exists():
        try:
            pid = int(CF_PID_FILE.read_text().strip())
            os.kill(pid, 9)
        except:
            pass
    
    proc = subprocess.Popen(
        [str(CF_BIN), "tunnel", "--url", f"http://localhost:{WEB_PORT}",
         "--protocol", "http2", "--no-autoupdate"],
        stdout=open(CF_LOG, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    CF_PID_FILE.write_text(str(proc.pid))
    
    # Wait for URL (up to 40s)
    for _ in range(20):
        time.sleep(2)
        url = get_tunnel_url()
        if url:
            CF_URL_FILE.write_text(url)
            log(f"✅ Tunnel up: {url}")
            return url
    log("❌ Tunnel URL timeout")
    return None


def update_helius(url):
    full_url = f"{url}/webhook/solana"
    if not CFG.exists():
        log(f"❌ No config at {CFG}")
        return
    
    config = json.loads(CFG.read_text())
    wallets = config.get("wallets", [])
    old_id = config.get("webhook_id", "")
    
    if old_id:
        try:
            req = urllib.request.Request(
                f"https://mainnet.helius-rpc.com/v0/webhooks/{old_id}?api-key={HEL_KEY}",
                method="DELETE"
            )
            urllib.request.urlopen(req, timeout=10)
        except:
            pass
    
    body = json.dumps({
        "webhookURL": full_url,
        "webhookType": "enhanced",
        "accountAddresses": wallets,
        "transactionTypes": ["SWAP"],
        "txnStatus": "success",
    }).encode()
    
    try:
        req = urllib.request.Request(
            "https://mainnet.helius-rpc.com/v0/webhooks?api-key=" + HEL_KEY,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            new_id = result.get("webhookID")
            if new_id:
                config["webhook_id"] = new_id
                config["url"] = full_url
                CFG.write_text(json.dumps(config, indent=2))
                log(f"✅ Helius updated: {new_id}")
                return
        log(f"❌ Helius update failed: no webhookID")
    except Exception as e:
        log(f"❌ Helius update error: {e}")


running = True
def stop(sig, frame):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

log("=== Supervisor starting ===")
log(f"PID: {os.getpid()}")

while running:
    # 1. Webhook server
    if not webhook_healthy():
        log("Webhook unhealthy, restarting")
        start_webhook()
    
    # 2. Tunnel
    if not tunnel_alive():
        log("Tunnel unhealthy, restarting")
        url = start_tunnel()
    else:
        url = get_tunnel_url()
    
    # 3. Helius webhook URL
    if url and CFG.exists():
        config = json.loads(CFG.read_text())
        saved_url = config.get("url", "")
        if saved_url != f"{url}/webhook/solana":
            log(f"URL drift detected: saved={saved_url}, current={url}/webhook/solana")
            update_helius(url)
    
    time.sleep(CHECK_INTERVAL)

log("=== Supervisor stopping ===")

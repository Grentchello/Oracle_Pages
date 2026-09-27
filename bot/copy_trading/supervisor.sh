#!/bin/bash
# Copy-trading supervisor v2 - simple, robust
# Monitors webhook + tunnel, restarts if dead, updates Helius on tunnel change

set +e

LOGS=/opt/data/hermes_work/bot/copy_trading/logs
mkdir -p "$LOGS" 2>/dev/null
SUP_LOG="$LOGS/supervisor.log"

WEB_PORT=8765
WEB_VENV=/opt/data/hermes_work/.venv/bin/python
WEB_SCRIPT=/opt/data/hermes_work/bot/copy_trader/webhook_server.py
WEB_DIR=/opt/data/hermes_work/bot/copy_trader
WEB_LOG="$LOGS/webhook.log"
WEB_PID_FILE="$LOGS/webhook.pid"

CF=/opt/data/home/.local/bin/cloudflared
CF_LOG=/tmp/cloudflared.log
CF_PID_FILE="$LOGS/cf.pid"

HEL_KEY="03b2d88f-daf1-4cdd-bbb1-a30351b0247a"
CFG="$WEB_DIR/cache/helius_webhook.json"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" >> "$SUP_LOG"
}

is_alive() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

start_webhook() {
    log "Starting webhook server..."
    cd "$WEB_DIR"
    nohup "$WEB_VENV" -u "$WEB_SCRIPT" >> "$WEB_LOG" 2>&1 &
    echo $! > "$WEB_PID_FILE"
    sleep 4
    if curl -s -m 3 "http://127.0.0.1:$WEB_PORT/health" > /dev/null; then
        log "✅ Webhook up (PID $(cat $WEB_PID_FILE))"
        return 0
    fi
    log "❌ Webhook failed to start"
    return 1
}

start_tunnel() {
    log "Starting tunnel..."
    rm -f "$CF_PID_FILE"
    nohup "$CF" tunnel --url "http://localhost:$WEB_PORT" --protocol http2 --no-autoupdate > "$CF_LOG" 2>&1 &
    echo $! > "$CF_PID_FILE"
    
    # Wait for URL
    for i in $(seq 1 20); do
        sleep 2
        URL=$(grep -oE "https://[a-z-]+\\.trycloudflare\\.com" "$CF_LOG" 2>/dev/null | head -1)
        if [ -n "$URL" ]; then
            echo "$URL" > "$LOGS/tunnel_url.txt"
            log "✅ Tunnel URL: $URL"
            return 0
        fi
    done
    log "❌ Tunnel URL timeout"
    return 1
}

get_tunnel_url() {
    if [ -f "$LOGS/tunnel_url.txt" ]; then
        cat "$LOGS/tunnel_url.txt"
    else
        grep -oE "https://[a-z-]+\\.trycloudflare\\.com" "$CF_LOG" 2>/dev/null | head -1
    fi
}

update_helius() {
    local url="$1"
    local full="${url}/webhook/solana"
    
    if [ ! -f "$CFG" ]; then
        log "No config file at $CFG"
        return 1
    fi
    
    local wallets=$(python3 -c "import json; d=json.load(open('$CFG')); print(json.dumps(d.get('wallets', [])))" 2>/dev/null)
    if [ -z "$wallets" ]; then
        log "No wallets in config"
        return 1
    fi
    
    local old_id=$(python3 -c "import json; d=json.load(open('$CFG')); print(d.get('webhook_id', ''))" 2>/dev/null)
    
    if [ -n "$old_id" ]; then
        curl -s -X DELETE "https://mainnet.helius-rpc.com/v0/webhooks/$old_id?api-key=$HEL_KEY" > /dev/null 2>&1
    fi
    
    local resp=$(curl -s -X POST "https://mainnet.helius-rpc.com/v0/webhooks?api-key=$HEL_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"webhookURL\": \"$full\", \"webhookType\": \"enhanced\", \"accountAddresses\": $wallets, \"transactionTypes\": [\"SWAP\"], \"txnStatus\": \"success\"}")
    
    local new_id=$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('webhookID', ''))" 2>/dev/null)
    
    if [ -n "$new_id" ]; then
        python3 -c "
import json
d = json.load(open('$CFG'))
d['webhook_id'] = '$new_id'
d['url'] = '$full'
json.dump(d, open('$CFG', 'w'), indent=2)
"
        log "✅ Helius updated: $new_id"
        return 0
    else
        log "❌ Helius update failed: $resp"
        return 1
    fi
}

# === Main logic ===
log "=== Supervisor check ==="

# 1. Webhook
if ! is_alive "$WEB_PID_FILE" || ! curl -s -m 3 "http://127.0.0.1:$WEB_PORT/health" > /dev/null 2>&1; then
    log "Webhook dead, restarting"
    if [ -f "$WEB_PID_FILE" ]; then
        kill -9 "$(cat $WEB_PID_FILE)" 2>/dev/null
    fi
    start_webhook
fi

# 2. Tunnel
if ! is_alive "$CF_PID_FILE"; then
    log "Tunnel dead, restarting"
    if [ -f "$CF_PID_FILE" ]; then
        kill -9 "$(cat $CF_PID_FILE)" 2>/dev/null
    fi
    start_tunnel
fi

# 3. Helius webhook URL
URL=$(get_tunnel_url)
SAVED=$(python3 -c "import json; d=json.load(open('$CFG')); print(d.get('url', ''))" 2>/dev/null)
if [ -n "$URL" ] && [ "$SAVED" != "${URL}/webhook/solana" ]; then
    log "URL changed: $URL, updating Helius"
    update_helius "$URL"
fi

log "✅ Done"

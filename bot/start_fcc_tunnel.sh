#!/bin/bash
# FCC + Cloudflare tunnel startup script
# Runs both the Free Claude Code server (if needed) and an ephemeral tunnel for phone access.
# Usage: ./start_fcc_tunnel.sh [restart|status|stop]

set -e

CLOUDFLARED=/opt/data/home/.local/bin/cloudflared
LOG_DIR=/opt/data/hermes_work/bot
TUNNEL_LOG=$LOG_DIR/tunnel.log
PID_FILE=$LOG_DIR/tunnel.pid

start_tunnel() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat $PID_FILE) 2>/dev/null; then
        echo "Tunnel already running (PID $(cat $PID_FILE))"
        grep -oE 'https://[a-z-]+\.trycloudflare\.com' $TUNNEL_LOG 2>/dev/null | head -1
        return 0
    fi

    # Make sure cloudflared is installed
    if [ ! -x "$CLOUDFLARED" ]; then
        echo "Installing cloudflared..."
        curl -fsSL -o "$CLOUDFLARED" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        chmod +x "$CLOUDFLARED"
    fi

    echo "Starting FCC tunnel (ephemeral, trycloudflare.com)..."
    nohup $CLOUDFLARED tunnel --url http://localhost:8082 --no-autoupdate > $TUNNEL_LOG 2>&1 &
    echo $! > $PID_FILE
    sleep 8
    URL=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' $TUNNEL_LOG 2>/dev/null | head -1)
    if [ -n "$URL" ]; then
        echo "✅ Tunnel live: $URL"
        echo "   Save this URL — it's your phone-accessible FCC admin."
    else
        echo "⚠ Tunnel starting... check $TUNNEL_LOG"
    fi
}

stop_tunnel() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        kill $PID 2>/dev/null || true
        rm -f $PID_FILE
        echo "Stopped tunnel PID $PID"
    fi
}

status_tunnel() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat $PID_FILE) 2>/dev/null; then
        echo "Tunnel running (PID $(cat $PID_FILE))"
        URL=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' $TUNNEL_LOG 2>/dev/null | head -1)
        echo "URL: $URL"
    else
        echo "Tunnel not running"
    fi
}

case "${1:-start}" in
    start)   start_tunnel ;;
    stop)    stop_tunnel ;;
    status)  status_tunnel ;;
    restart) stop_tunnel; start_tunnel ;;
    *)       echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac

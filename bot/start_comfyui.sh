#!/bin/bash
# ComfyUI + Cloudflare tunnel startup script
# Usage: ./start_comfyui.sh [start|stop|status|restart]

set -e

COMFYUI_DIR="/opt/data/home/comfy/ComfyUI"
CLOUDFLARED="/opt/data/home/.local/bin/cloudflared"
LOG_DIR="/opt/data/hermes_work/bot"
COMFYUI_LOG="$LOG_DIR/comfyui.log"
TUNNEL_LOG="$LOG_DIR/comfyui_tunnel.log"
PID_FILE="$LOG_DIR/comfyui.pid"
TUNNEL_PID_FILE="$LOG_DIR/comfyui_tunnel.pid"

start_comfyui() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat $PID_FILE) 2>/dev/null; then
        echo "ComfyUI already running (PID $(cat $PID_FILE))"
        return 0
    fi

    echo "Starting ComfyUI (CPU mode)..."
    cd "$COMFYUI_DIR"
    nohup "$COMFYUI_DIR/.venv/bin/python" main.py --listen 0.0.0.0 --port 8188 --cpu --disable-cuda-malloc > "$COMFYUI_LOG" 2>&1 &
    echo $! > "$PID_FILE"
    echo "ComfyUI starting (PID $!)"
    sleep 5
    if curl -sS http://localhost:8188/system_stats >/dev/null 2>&1; then
        echo "✅ ComfyUI ready at http://localhost:8188"
    else
        echo "⚠ ComfyUI still starting... check $COMFYUI_LOG"
    fi
}

start_tunnel() {
    if [ -f "$TUNNEL_PID_FILE" ] && kill -0 $(cat $TUNNEL_PID_FILE) 2>/dev/null; then
        echo "Tunnel already running (PID $(cat $TUNNEL_PID_FILE))"
        grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1
        return 0
    fi

    echo "Starting Cloudflare tunnel..."
    nohup "$CLOUDFLARED" tunnel --url http://localhost:8188 --no-autoupdate > "$TUNNEL_LOG" 2>&1 &
    echo $! > "$TUNNEL_PID_FILE"
    sleep 8
    URL=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
    if [ -n "$URL" ]; then
        echo "✅ Tunnel live: $URL"
    else
        echo "⚠ Tunnel starting... check $TUNNEL_LOG"
    fi
}

stop_all() {
    if [ -f "$TUNNEL_PID_FILE" ]; then
        kill $(cat $TUNNEL_PID_FILE) 2>/dev/null || true
        rm -f "$TUNNEL_PID_FILE"
        echo "Stopped tunnel"
    fi
    if [ -f "$PID_FILE" ]; then
        kill $(cat $PID_FILE) 2>/dev/null || true
        rm -f "$PID_FILE"
        echo "Stopped ComfyUI"
    fi
}

status() {
    echo "=== ComfyUI ==="
    if [ -f "$PID_FILE" ] && kill -0 $(cat $PID_FILE) 2>/dev/null; then
        echo "Running (PID $(cat $PID_FILE))"
    else
        echo "Not running"
    fi
    echo "=== Tunnel ==="
    if [ -f "$TUNNEL_PID_FILE" ] && kill -0 $(cat $TUNNEL_PID_FILE) 2>/dev/null; then
        echo "Running (PID $(cat $TUNNEL_PID_FILE))"
        URL=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
        echo "URL: $URL"
    else
        echo "Not running"
    fi
}

case "${1:-start}" in
    start)   start_comfyui; start_tunnel ;;
    stop)    stop_all ;;
    status)  status ;;
    restart) stop_all; sleep 2; start_comfyui; start_tunnel ;;
    *)       echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac

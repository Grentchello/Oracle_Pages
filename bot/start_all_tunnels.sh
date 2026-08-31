#!/bin/bash
# Start both FCC + ComfyUI tunnels (Cloudflare ephemeral)
# Usage: ./start_all_tunnels.sh [start|stop|status|restart]

set -e

CLOUDFLARED="/opt/data/home/.local/bin/cloudflared"
LOG_DIR="/opt/data/hermes_work/bot"
URL_FILE="$LOG_DIR/tunnel_urls.txt"

start_tunnel() {
    local name=$1 port=$2 pid_file=$3 log_file=$4

    if [ -f "$pid_file" ] && kill -0 $(cat $pid_file) 2>/dev/null; then
        local url=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$log_file" 2>/dev/null | head -1)
        echo "$name: running (PID $(cat $pid_file)) → $url"
        return 0
    fi

    echo "Starting $name tunnel on port $port..."
    nohup "$CLOUDFLARED" tunnel --url "http://localhost:$port" --no-autoupdate > "$log_file" 2>&1 &
    echo $! > "$pid_file"
    sleep 8
    local url=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$log_file" 2>/dev/null | head -1)
    if [ -n "$url" ]; then
        echo "✅ $name: $url"
    else
        echo "⚠ $name: still starting... check $log_file"
    fi
}

stop_tunnel() {
    local pid_file=$1 name=$2
    if [ -f "$pid_file" ]; then
        kill $(cat $pid_file) 2>/dev/null || true
        rm -f "$pid_file"
        echo "Stopped $name"
    fi
}

start_all() {
    # Start ComfyUI server if not running
    local comfy_pid="$LOG_DIR/comfyui.pid"
    if [ -f "$comfy_pid" ] && kill -0 $(cat $comfy_pid) 2>/dev/null; then
        echo "ComfyUI server: running"
    else
        echo "Starting ComfyUI server..."
        cd /opt/data/home/comfy/ComfyUI
        nohup .venv/bin/python main.py --listen 0.0.0.0 --port 8188 --cpu --disable-cuda-malloc > "$LOG_DIR/comfyui.log" 2>&1 &
        echo $! > "$comfy_pid"
        echo "ComfyUI starting (PID $!)"
        sleep 5
    fi

    start_tunnel "FCC" 8082 "$LOG_DIR/fcc_tunnel.pid" "$LOG_DIR/fcc_tunnel.log"
    start_tunnel "ComfyUI" 8188 "$LOG_DIR/comfyui_tunnel.pid" "$LOG_DIR/comfyui_tunnel.log"

    # Save URLs
    echo "=== Tunnel URLs ===" > "$URL_FILE"
    grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$LOG_DIR/fcc_tunnel.log" 2>/dev/null | head -1 | xargs -I{} echo "FCC: {}" >> "$URL_FILE"
    grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$LOG_DIR/comfyui_tunnel.log" 2>/dev/null | head -1 | xargs -I{} echo "ComfyUI: {}" >> "$URL_FILE"
    echo ""
    cat "$URL_FILE"
}

stop_all() {
    stop_tunnel "$LOG_DIR/comfyui_tunnel.pid" "ComfyUI tunnel"
    stop_tunnel "$LOG_DIR/fcc_tunnel.pid" "FCC tunnel"
    # Stop ComfyUI server
    local comfy_pid="$LOG_DIR/comfyui.pid"
    if [ -f "$comfy_pid" ]; then
        kill $(cat $comfy_pid) 2>/dev/null || true
        rm -f "$comfy_pid"
        echo "Stopped ComfyUI server"
    fi
}

status() {
    echo "=== ComfyUI Server ==="
    local comfy_pid="$LOG_DIR/comfyui.pid"
    if [ -f "$comfy_pid" ] && kill -0 $(cat $comfy_pid) 2>/dev/null; then
        echo "Running (PID $(cat $comfy_pid))"
    else
        echo "Not running"
    fi

    echo "=== FCC Tunnel ==="
    local fcc_pid="$LOG_DIR/fcc_tunnel.pid"
    if [ -f "$fcc_pid" ] && kill -0 $(cat $fcc_pid) 2>/dev/null; then
        local url=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$LOG_DIR/fcc_tunnel.log" 2>/dev/null | head -1)
        echo "Running → $url"
    else
        echo "Not running"
    fi

    echo "=== ComfyUI Tunnel ==="
    local comfy_t_pid="$LOG_DIR/comfyui_tunnel.pid"
    if [ -f "$comfy_t_pid" ] && kill -0 $(cat $comfy_t_pid) 2>/dev/null; then
        local url=$(grep -oE 'https://[a-z-]+\.trycloudflare\.com' "$LOG_DIR/comfyui_tunnel.log" 2>/dev/null | head -1)
        echo "Running → $url"
    else
        echo "Not running"
    fi
}

case "${1:-start}" in
    start)   start_all ;;
    stop)    stop_all ;;
    status)  status ;;
    restart) stop_all; sleep 2; start_all ;;
    *)       echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac

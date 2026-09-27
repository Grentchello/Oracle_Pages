#!/bin/bash
# Start cloudflared quick tunnel for Multica (port 3300)
# Writes URL to /var/log/multica-tunnel/url.txt for later recovery
set +e

LOG_DIR=/var/log/multica-tunnel
PID_FILE=$LOG_DIR/tunnel.pid
LOG_FILE=$LOG_DIR/tunnel.log
mkdir -p "$LOG_DIR"

# Kill any prior tunnel
if [ -f "$PID_FILE" ]; then
  OLDPID=$(cat "$PID_FILE")
  if kill -0 "$OLDPID" 2>/dev/null; then
    kill "$OLDPID" 2>/dev/null
    sleep 2
    kill -9 "$OLDPID" 2>/dev/null
  fi
  rm -f "$PID_FILE"
fi

# also nuke any orphan cloudflared
pkill -9 -f "cloudflared tunnel --url http://localhost:3300" 2>/dev/null
sleep 1

# Start tunnel fully detached
setsid nohup /root/.local/bin/cloudflared tunnel --url http://localhost:3300 --no-autoupdate --protocol http2 \
  > "$LOG_FILE" 2>&1 < /dev/null &
NEWPID=$!
echo "$NEWPID" > "$PID_FILE"
disown

# wait for URL
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 2
  URL=$(grep -oE "https://[a-z-]+\.trycloudflare\.com" "$LOG_FILE" 2>/dev/null | head -1)
  if [ -n "$URL" ]; then
    echo "$URL" > "$LOG_DIR/url.txt"
    echo "PID: $NEWPID"
    echo "URL: $URL"
    exit 0
  fi
done

echo "FAILED — tunnel log:"
cat "$LOG_FILE"
exit 1

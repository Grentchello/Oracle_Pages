#!/bin/bash
# Patch the web image's hardcoded ws://localhost:8080/ws to use the tunnel URL
WS_URL='wss://charlotte-blackjack-ecology-accomplish.trycloudflare.com/ws'

echo "=== patch the bundle ==="
docker exec web-auceguju4j2ty0xs07bgd1xx sh -c "
# backup
cp /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js /tmp/24550.js.bak
# patch with sed
sed -i 's|ws://localhost:8080/ws||g' /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js
# verify
grep -o 'wss?://[a-zA-Z0-9.:/-]+' /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js | sort -u
"
echo
echo "=== restart the web container ==="
docker restart web-auceguju4j2ty0xs07bgd1xx
sleep 5
echo
echo "=== verify container is up ==="
docker ps --format "{{.Names}}\t{{.Status}}" | grep web-auceguju4j2ty0xs07bgd1xx

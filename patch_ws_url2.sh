#!/bin/bash
WS_URL='wss://charlotte-blackjack-ecology-accomplish.trycloudflare.com/ws'

echo "=== confirm file exists ==="
docker exec web-auceguju4j2ty0xs07bgd1xx ls -la /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js

echo "=== current content (ws URLs only) ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -oE 'wss?://[a-zA-Z0-9.:/-]+' /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js | sort -u

echo "=== sed patch ==="
docker exec web-aucegu4j2ty0xs07bgd1xx 2>/dev/null
docker exec web-auceguju4j2ty0xs07bgd1xx sh <<PATCH
cp /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js /tmp/24550.js.bak
sed -i "s|ws://localhost:8080/ws|${WS_URL}|g" /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js
PATCH

echo "=== after patch ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -oE 'wss?://[a-zA-Z0-9.:/-]+' /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js | sort -u

echo "=== restart ==="
docker restart web-auceguju4j2ty0xs07bgd1xx
sleep 5
docker ps --format '{{.Names}}\t{{.Status}}' | grep web-aucegu4j2ty0xs07bgd1xx

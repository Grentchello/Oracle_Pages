#!/bin/bash
echo "=== all ws:// and wss:// references in web bundle ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -rohE "wss?://[a-zA-Z0-9.:/-]+" /app/apps/web/.next/ 2>/dev/null | sort -u
echo "---"
echo "=== check for NEXT_PUBLIC_WS_URL usage ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -rl "NEXT_PUBLIC_WS_URL" /app/apps/web/.next/ 2>/dev/null | head
echo "---"
echo "=== check the WS chunk 24550 for context ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -o "ws://localhost:8080/ws" /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js
docker exec web-auceguju4j2ty0xs07bgd1xx grep -c "ws://localhost:8080/ws" /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js

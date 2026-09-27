#!/bin/bash
echo "=== ALL hardcoded localhost/127.0.0.1 references in the web bundle ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -rohE "https?://localhost:[0-9]+|wss?://localhost:[0-9]+|https?://127\\.0\\.0\\.1:[0-9]+|wss?://127\\.0\\.0\\.1:[0-9]+" /app/apps/web/.next/ 2>/dev/null | sort -u
echo "---"
echo "=== check WS chunk specifically ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -oE "wss?://[a-zA-Z0-9.:/-]+" /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js | sort -u
echo "---"
echo "=== look in login page chunk (73100) for any URLs ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -oE "https?://[a-zA-Z0-9.:/-]+|wss?://[a-zA-Z0-9.:/-]+" /app/apps/web/.next/static/chunks/73100*.js 2>/dev/null | sort -u
echo "---"
echo "=== look in app page chunk ==="
docker exec web-auceguju4j2ty0xs07bgd1xx ls /app/apps/web/.next/static/chunks/app/\(auth\)/ 2>/dev/null
echo "---"
echo "=== look in login page chunk (where sendCode lives) ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -oE "https?://[a-zA-Z0-9.:/-]+|wss?://[a-zA-Z0-9.:/-]+|localhost|127\\.0\\.0\\.1" /app/apps/web/.next/server/app/\(auth\)/login/page.js 2>/dev/null | sort -u | head -20

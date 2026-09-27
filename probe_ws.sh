#!/bin/bash
ssh -i /opt/data/home/.ssh/coolify_host_key -o StrictHostKeyChecking=no root@207.211.145.179 '
echo "=== all ws:// references in web bundle ==="
docker exec web-auceguju4j2ty0xs07bgd1xx sh <<'"'"'INNER'"'"'
grep -roE "ws://[a-zA-Z0-9.:-]+" /app/apps/web/.next/ 2>/dev/null | sort -u
echo ---
grep -roE "wss://[a-zA-Z0-9.:-]+" /app/apps/web/.next/ 2>/dev/null | sort -u
echo ---
grep -roE "NEXT_PUBLIC_WS_URL" /app/apps/web/.next/ 2>/dev/null | sort -u | head
INNER
'

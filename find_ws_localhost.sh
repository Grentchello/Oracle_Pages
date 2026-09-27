#!/bin/bash
echo "=== find files containing ws://localhost ==="
docker exec web-auceguju4j2ty0xs07bgd1xx grep -rl "ws://localhost" /app/apps/web/.next/ 2>/dev/null

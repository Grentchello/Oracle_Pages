#!/bin/bash
WS_URL='wss://charlotte-blackjack-ecology-accomplish.trycloudflare.com/ws'
CORRECT="web-auceguju4j2ty0xs07bgd1xx"
TARGET="/app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js"

echo "=== 1. Current WS URL ==="
docker exec $CORRECT grep -oE 'wss?://[a-zA-Z0-9.:/-]+' $TARGET | sort -u

echo "=== 2. Apply sed patch ==="
docker exec $CORRECT sh -c "
sed -i 's|ws://localhost:8080/ws|$WS_URL|g' $TARGET
echo 'After patch:'
grep -oE 'wss?://[a-zA-Z0-9.:/-]+' $TARGET | sort -u
"

echo "=== 3. Set up init script that re-applies patch on container start ==="
# Create a custom entrypoint script that patches the bundle before starting Next.js
INIT_SCRIPT='/usr/local/bin/patch-and-start.sh'
docker exec $CORRECT sh -c "
cat > $INIT_SCRIPT << 'EOF'
#!/bin/sh
TARGET=/app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js
if [ -f \$TARGET ]; then
  sed -i 's|ws://localhost:8080/ws|wss://charlotte-blackjack-ecology-accomplish.trycloudflare.com/ws|g' \$TARGET
fi
exec node server.js
EOF
chmod +x $INIT_SCRIPT
"

echo "=== 4. Verify init script ==="
docker exec $CORRECT cat $INIT_SCRIPT

echo "=== 5. Find the original entrypoint ==="
docker exec $CORRECT cat /app/apps/web/package.json 2>/dev/null | grep -A3 scripts | head -10
docker exec $CORRECT cat /app/package.json 2>/dev/null | head -30
docker exec $CORRECT ls /app/entrypoint*.sh /docker-entrypoint*.sh 2>/dev/null

#!/bin/bash
# Diagnose why build isn't progressing

CONTAINER="fkixrzsd46heahatuspb89aj"

echo "=== 1. DNS from container ==="
docker exec $CONTAINER sh -c 'cat /etc/resolv.conf; echo "---"; nslookup registry-1.docker.io 2>&1 || getent hosts registry-1.docker.io'

echo ""
echo "=== 2. Direct curl to registry ==="
docker exec $CONTAINER sh -c 'curl -sS -v -m 10 -o /dev/null https://registry-1.docker.io/v2/ 2>&1 | head -20'

echo ""
echo "=== 3. DNS for ghcr.io ==="
docker exec $CONTAINER sh -c 'getent hosts ghcr.io'

echo ""
echo "=== 4. Host DNS ==="
getent hosts registry-1.docker.io
cat /etc/resolv.conf

echo ""
echo "=== 5. iptables on host ==="
iptables -L -n -v 2>&1 | head -20

echo ""
echo "=== 6. Check if container has any DROP rules ==="
docker exec $CONTAINER sh -c 'iptables -L 2>&1 | head -10'

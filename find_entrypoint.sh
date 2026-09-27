#!/bin/bash
echo "=== image config ==="
docker image inspect ghcr.io/multica-ai/multica-web:latest 2>&1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
if isinstance(d, list):
    d = d[0]
cfg = d.get('Config', {})
print('Entrypoint:', cfg.get('Entrypoint'))
print('Cmd:', cfg.get('Cmd'))
print('WorkingDir:', cfg.get('WorkingDir'))
"
echo
echo "=== find entrypoint script ==="
docker run --rm --entrypoint sh ghcr.io/multica-ai/multica-web:latest -c "ls /docker-entrypoint* /entrypoint* /usr/local/bin/docker-entrypoint* 2>&1; echo ---; cat /docker-entrypoint.sh 2>&1 | head -20"

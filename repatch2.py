#!/usr/bin/env python3
import urllib.request
import json
import base64
import subprocess
import time
import re

API = "http://207.211.145.179:8000/api/v1"
TOKEN = "2|N3WNji5HjoQHISZFNIUTayI1wwN5AVhhiMaXrwj2b07cf2a0"
SERVICE_UUID = "honkekh3rpaqbostmn0eplvv"


def call(method, endpoint, data=None):
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    else:
        body = None
    req = urllib.request.Request(f"{API}{endpoint}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            c = r.read().decode()
            try:
                return r.status, json.loads(c) if c else None
            except json.JSONDecodeError:
                return r.status, c[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='ignore')[:2000]


# Get current compose
status, svc = call('GET', f'/services/{SERVICE_UUID}')
compose = svc['docker_compose']

# Strip command blocks
lines = compose.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip() == "command:":
        i += 1
        while i < len(lines) and (re.match(r'^\s+-\s', lines[i]) or lines[i].strip() == ''):
            i += 1
        continue
    new_lines.append(line)
    i += 1

compose = '\n'.join(new_lines)

# Use double quotes for the YAML value, no inner single quotes issue
# Format: command: ["sh", "-c", "bash /patches/... && exec node ..."]
cmd_line = '    command: ["sh", "-c", "bash /patches/hermes-bootstrap.sh && exec node --import ./server/node_modules/tsx/dist/loader.mjs server/dist/index.js"]\n'

compose = compose.replace(
    "    container_name: paperclip-honkekh3rpaqbostmn0eplvv\n",
    cmd_line + "    container_name: paperclip-honkekh3rpaqbostmn0eplvv\n",
    1
)

# PATCH
status, resp = call('PATCH', f'/services/{SERVICE_UUID}', {
    'docker_compose_raw': base64.b64encode(compose.encode()).decode(),
})
print(f'Update: {status} {str(resp)[:300]}')

if status == 200:
    s, r = call('POST', f'/services/{SERVICE_UUID}/restart', {})
    print(f'Restart: {s} {r}')

time.sleep(30)

r = subprocess.run(
    ["ssh", "-i", "/opt/data/home/.ssh/coolify_host_key", "-o", "StrictHostKeyChecking=no",
     "root@207.211.145.179",
     "docker ps --filter name=paperclip-honkekh3rpaqbostmn0eplvv --format '{{.Status}}' 2>&1; echo ---HTTP---; curl -sS -m 5 -o /dev/null -w 'HTTP %{http_code}\\n' http://207.211.145.179:3100/ 2>&1; echo ---LOGS---; docker logs paperclip-honkekh3rpaqbostmn0eplvv --tail 25 2>&1 | tail -20"],
    capture_output=True, text=True, timeout=20
)
print(r.stdout[:5000])

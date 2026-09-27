#!/usr/bin/env python3
import urllib.request
import json
import base64
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


status, svc = call('GET', f'/services/{SERVICE_UUID}')
compose = svc['docker_compose']

# Remove any command block (multiple variants)
lines = compose.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip() == "command:":
        # Skip this and all following list/dash lines
        i += 1
        while i < len(lines):
            nxt = lines[i]
            # If it's still part of the command (starts with whitespace + dash), skip
            if re.match(r'^\s+-\s', nxt) or re.match(r'^\s+-\s', nxt):
                i += 1
            else:
                break
        continue
    new_lines.append(line)
    i += 1

patched = '\n'.join(new_lines)

# Add bind mount - find the /paperclip volume line
bind_mount = "      - '/var/lib/docker/volumes/honkekh3rpaqbostmn0eplvv_paperclip-data/_data/patches/ai-connections.js:/app/server/dist/routes/ai-connections.js:ro'"

# Find any line with ':/paperclip' and insert before it
out_lines = []
inserted = False
for line in patched.split('\n'):
    if ':/paperclip' in line and not inserted:
        out_lines.append(bind_mount)
        inserted = True
    out_lines.append(line)
patched = '\n'.join(out_lines)

if 'command:' in patched:
    print('⚠️ command: still present')
else:
    print('✅ command removed')

if inserted:
    print('✅ bind mount added')
else:
    print('❌ no /paperclip volume line found')

print('\n=== Preview (volumes section) ===')
for ln in patched.split('\n'):
    if 'volume' in ln or ':/paperclip' in ln or 'patches' in ln or 'ai-connections' in ln:
        print(ln)

status, resp = call('PATCH', f'/services/{SERVICE_UUID}', {
    'docker_compose_raw': base64.b64encode(patched.encode()).decode(),
})
print(f'\nUpdate: {status} {resp}')

if status == 200:
    s, r = call('POST', f'/services/{SERVICE_UUID}/restart', {})
    print(f'Restart: {s} {r}')

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

# Find the broken command block
# It's lines like:
#     command:
#       - sh
#       - '-c'
#       - "python3 -c \"...\""

# Remove the entire command block - everything from "    command:" until the next line that starts with 4 spaces and a non-whitespace, non-"-" character
lines = compose.split('\n')
new_lines = []
i = 0
removed = False
while i < len(lines):
    line = lines[i]
    if line == "    command:" and not removed:
        # Skip this line and all following lines that start with "      -" until we hit one that doesn't
        i += 1
        while i < len(lines) and (lines[i].startswith("      -") or lines[i].strip() == ''):
            # Stop if we hit a non-list line (start of next YAML field)
            if i > 0 and lines[i].startswith("    ") and not lines[i].startswith("      -"):
                break
            i += 1
        removed = True
        continue
    new_lines.append(line)
    i += 1

patched = '\n'.join(new_lines)

# Now add the bind mount for our patched file
volume_block = "      - 'honkekh3rpaqbostmn0eplvv_honkekh3rpaqbostmn0eplvv-paperclip-data:/paperclip'"
bind_mount = "      - '/var/lib/docker/volumes/honkekh3rpaqbostmn0eplvv_paperclip-data/_data/patches/ai-connections.js:/app/server/dist/routes/ai-connections.js:ro'"
patched = patched.replace(volume_block, bind_mount + "\n" + volume_block, 1)

# Verify
if 'command:' in patched:
    print('⚠️ command: still present')
else:
    print('✅ command removed cleanly')

if bind_mount in patched:
    print('✅ bind mount added')
else:
    print('❌ bind mount NOT added')

# Preview top 12 lines
print('\n=== Preview (top 15 lines) ===')
for ln in patched.split('\n')[:15]:
    print(ln)

# Update
status, resp = call('PATCH', f'/services/{SERVICE_UUID}', {
    'docker_compose_raw': base64.b64encode(patched.encode()).decode(),
})
print(f'\nUpdate: {status} {resp}')

if status == 200:
    print('\nRestarting...')
    s, r = call('POST', f'/services/{SERVICE_UUID}/restart', {})
    print(f'Restart: {s} {r}')

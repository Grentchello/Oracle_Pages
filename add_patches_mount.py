#!/usr/bin/env python3
import urllib.request
import json
import base64

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

# Add bind-mount for patches dir (read-only) so bootstrap script is accessible
patches_mount = "      - '/var/lib/docker/volumes/honkekh3rpaqbostmn0eplvv_paperclip-data/_data/patches:/patches:ro'"
js_mount = "      - '/var/lib/docker/volumes/honkekh3rpaqbostmn0eplvv_paperclip-data/_data/patches/ai-connections.js:/app/server/dist/routes/ai-connections.js:ro'"

# Insert patches mount after JS mount
if '/patches:ro' not in compose:
    compose = compose.replace(js_mount, js_mount + "\n" + patches_mount, 1)
    print("✅ Patches mount added")
else:
    print("⚠️ Patches mount already present")

# Update
status, resp = call('PATCH', f'/services/{SERVICE_UUID}', {
    'docker_compose_raw': base64.b64encode(compose.encode()).decode(),
})
print(f'\nUpdate: {status} {resp}')

if status == 200:
    s, r = call('POST', f'/services/{SERVICE_UUID}/restart', {})
    print(f'Restart: {s} {r}')

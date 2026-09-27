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


# Get current compose
status, svc = call('GET', f'/services/{SERVICE_UUID}')
print(f'Status: {status}')
if isinstance(svc, dict):
    print(f'Compose:')
    print(svc.get('docker_compose'))
    print('---')
    print(f'Compose raw (base64): {svc.get("docker_compose_raw", "")[:500]}')

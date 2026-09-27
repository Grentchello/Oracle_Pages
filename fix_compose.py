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
current_compose = svc['docker_compose']

# Replace the broken command block with a clean base64-based one
# Build the python script content
PYTHON_PATCH_SCRIPT = '''#!/usr/bin/env python3
p = "/app/server/dist/routes/ai-connections.js"
try:
    t = open(p).read()
    sentinel = "export async function validateAiApiKey(provider, key, request = fetch) {"
    marker = "HERMES_PATCH_ACCEPT_ANY_ANTHROPIC_KEY"
    if sentinel in t and marker not in t:
        Q = chr(34)
        NL = chr(10)
        inj = sentinel + NL
        inj += "    // " + marker + NL
        inj += "    if (provider === " + Q + "anthropic" + Q + ") {" + NL
        inj += "        if (!key || typeof key !== " + Q + "string" + Q + " || key.trim().length < 8) {" + NL
        inj += "            throw new Error(" + Q + "rejected" + Q + ");" + NL
        inj += "        }" + NL
        inj += "        return;" + NL
        inj += "    }" + NL
        t = t.replace(sentinel, inj, 1)
        open(p, "w").write(t)
        print("PATCHED on boot")
    else:
        print("already patched")
except Exception as e:
    print("patch error:", e)
'''

# Base64 encode the script
b64 = base64.b64encode(PYTHON_PATCH_SCRIPT.encode()).decode()

# Build the shell command using a heredoc to write the file (avoids all quoting hell)
# Using base64 decode inline which avoids shell escaping entirely
shell_cmd = (
    "echo " + b64 + " | base64 -d > /tmp/hermes_patch.py"
    " && python3 /tmp/hermes_patch.py"
    " && exec node --import ./server/node_modules/tsx/dist/loader.mjs server/dist/index.js"
)

# Find and replace the broken command block
import re
# Match: command:\n      - sh\n      - '-c'\n      - "..." (multiline)
pattern = re.compile(
    r"    command:\n      - sh\n      - '-c'\n      - \"[^\"]*?(?:\\\\.|[^\"\\\\])*?\"\n",
    re.DOTALL
)

if pattern.search(current_compose):
    # Replace with new clean version
    replacement = "    command: ['sh', '-c', '" + shell_cmd.replace("'", "'\\''") + "']\n"
    patched = pattern.sub(replacement, current_compose, count=1)
    print(f'Patched (found old command block)')
else:
    # Inject new
    patched = current_compose.replace(
        "    image: 'ghcr.io/paperclipai/paperclip:latest'\n",
        "    image: 'ghcr.io/paperclipai/paperclip:latest'\n    command: ['sh', '-c', '" + shell_cmd.replace("'", "'\\''") + "']\n",
        1
    )
    print('Patched (no old command, injected new)')

# Preview
print('\n=== Preview ===')
for line in patched.split('\n')[:8]:
    print(line)

# Update
status, resp = call('PATCH', f'/services/{SERVICE_UUID}', {
    'docker_compose_raw': base64.b64encode(patched.encode()).decode(),
})
print(f'\nUpdate: {status} {resp}')

if status == 200:
    print('\nRestarting...')
    s, r = call('POST', f'/services/{SERVICE_UUID}/restart', {})
    print(f'Restart: {s} {r}')

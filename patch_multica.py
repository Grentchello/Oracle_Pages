#!/usr/bin/env python3
"""Patch multica compose to publish host ports and redeploy."""
import base64
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

for line in Path("/opt/data/.config/coolify/multica.env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

API = os.environ["COOLIFY_API_BASE"]
TOKEN = os.environ["COOLIFY_API_TOKEN"]
HOST = os.environ["COOLIFY_HOST"]
RESEND_KEY = os.environ["RESEND_API_KEY"]
PROJECT_UUID = "lrgytuw9ufwuy8jmrpyxygyz"
ENV_UUID = "lssd4k4jrjebjd2p5m3fsezb"
SERVICE_UUID = "auceguju4j2ty0xs07bgd1xx"


def call(method, endpoint, data=None):
    url = f"{API}{endpoint}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            content = r.read().decode()
            try:
                return r.status, json.loads(content) if content else None
            except json.JSONDecodeError:
                return r.status, content[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")[:2000]
    except Exception as e:
        return None, str(e)


def ssh(cmd, timeout=30):
    return subprocess.run(
        ["ssh", "-i", os.environ["COOLIFY_SSH_KEY"], "-o", "StrictHostKeyChecking=no",
         f"root@{HOST}", cmd],
        capture_output=True, text=True, timeout=timeout,
    )


# Reuse secrets from previous state
state = json.loads(Path("/opt/data/.config/coolify/multica_state.json").read_text())
jwt_secret = state["jwt_secret"]
db_password = state["db_password"]
vcs_secret = state["vcs_secret"]
print("reusing existing secrets")

# Compose with actual host port mappings (Coolify auto-picks ports if empty)
# Pick ports that are unlikely to clash with the running services (paperclip 3100,
# Hermes 8642/9119, litellm 4000). Going with 3300 (web) + 8380 (backend).
WEB_PORT = 3300
BACKEND_PORT = 8380

compose = f"""services:
  postgres:
    image: pgvector/pgvector:pg17
    restart: unless-stopped
    environment:
      POSTGRES_DB: multica
      POSTGRES_USER: multica
      POSTGRES_PASSWORD: {db_password}
    volumes:
      - multica_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U multica -d multica"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    image: ghcr.io/multica-ai/multica-backend:latest
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://multica:{db_password}@postgres:5432/multica?sslmode=disable
      JWT_SECRET: {jwt_secret}
      MULTICA_VCS_SECRET_KEY: {vcs_secret}
      PORT: "8080"
      FRONTEND_ORIGIN: http://{HOST}:{WEB_PORT}
      APP_ENV: production
      RESEND_API_KEY: {RESEND_KEY}
      RESEND_FROM_EMAIL: noreply@multica.ai
    volumes:
      - multica_uploads:/app/data/uploads
    ports:
      - "{BACKEND_PORT}:8080"

  web:
    image: ghcr.io/multica-ai/multica-web:latest
    restart: unless-stopped
    depends_on:
      - backend
    environment:
      PORT: "3000"
      NEXT_PUBLIC_API_URL: http://{HOST}:{BACKEND_PORT}
    ports:
      - "{WEB_PORT}:3000"

volumes:
  multica_pgdata:
    name: multica_pgdata
  multica_uploads:
    name: multica_uploads
"""

print(f"\nnew compose: web={WEB_PORT}, backend={BACKEND_PORT}")

# --- stop the old service first ---
print("\n=== stopping current service ===")
status, resp = call("POST", f"/services/{SERVICE_UUID}/stop", {})
print(f"stop: {status} {str(resp)[:300]}")

# --- patch docker_compose_raw ---
print("\n=== patching compose ===")
status, resp = call("PATCH", f"/services/{SERVICE_UUID}", {
    "docker_compose_raw": base64.b64encode(compose.encode()).decode(),
})
print(f"patch: {status} {str(resp)[:300]}")

# --- start ---
print("\n=== starting ===")
time.sleep(2)
status, resp = call("POST", f"/services/{SERVICE_UUID}/start", {})
print(f"start: {status} {str(resp)[:300]}")

# --- poll ---
print("\n=== polling (45s window) ===")
for i in range(6):
    time.sleep(8)
    status, svc = call("GET", f"/services/{SERVICE_UUID}")
    if isinstance(svc, dict):
        print(f"  t+{8*(i+1)}s status={svc.get('status')!r}  ports={svc.get('ports')!r}  fqdn={svc.get('fqdn')!r}")
    else:
        print(f"  t+{8*(i+1)}s {svc}")

# --- verify host ports actually bind ---
print("\n=== checking host port bindings ===")
ssh_result = ssh('docker ps -a --format "{{.Names}}\t{{.Ports}}" | grep -E "auceguju4j2ty0xs07bgd1xx"')
print(ssh_result.stdout)

# Save final state
Path("/opt/data/.config/coolify/multica_state.json").write_text(json.dumps({
    **state,
    "web_port": WEB_PORT,
    "backend_port": BACKEND_PORT,
    "compose": compose,
}, indent=2))

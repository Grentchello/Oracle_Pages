#!/usr/bin/env python3
"""Patch multica service to use Resend's pre-verified onresend.com subdomain."""
import base64
import json
import os
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


# Load existing state to reuse secrets
state = json.loads(Path("/opt/data/.config/coolify/multica_state.json").read_text())
jwt_secret = state["jwt_secret"]
db_password = state["db_password"]
vcs_secret = state["vcs_secret"]
web_port = state["web_port"]
backend_port = state["backend_port"]

# Switch to Resend's pre-verified subdomain (works for all Resend accounts)
NEW_FROM = "Multica <onboarding@resend.dev>"  # Resend's universal test sender, works on free tier

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
      FRONTEND_ORIGIN: http://{HOST}:{web_port}
      APP_ENV: production
      RESEND_API_KEY: {RESEND_KEY}
      RESEND_FROM_EMAIL: {NEW_FROM}
    volumes:
      - multica_uploads:/app/data/uploads
    ports:
      - "{backend_port}:8080"

  web:
    image: ghcr.io/multica-ai/multica-web:latest
    restart: unless-stopped
    depends_on:
      - backend
    environment:
      PORT: "3000"
      NEXT_PUBLIC_API_URL: http://{HOST}:{backend_port}
    ports:
      - "{web_port}:3000"

volumes:
  multica_pgdata:
    name: multica_pgdata
  multica_uploads:
    name: multica_uploads
"""

print(f"new RESEND_FROM_EMAIL: {NEW_FROM}")

# Stop -> patch -> start
print("\n=== stop ===")
call("POST", f"/services/{SERVICE_UUID}/stop", {})
time.sleep(3)

print("=== patch ===")
status, resp = call("PATCH", f"/services/{SERVICE_UUID}", {
    "docker_compose_raw": base64.b64encode(compose.encode()).decode(),
})
print(f"patch: {status} {str(resp)[:200]}")

time.sleep(2)
print("=== start ===")
status, resp = call("POST", f"/services/{SERVICE_UUID}/start", {})
print(f"start: {status} {str(resp)[:200]}")

# Poll
print("\n=== poll ===")
for i in range(8):
    time.sleep(8)
    _, svc = call("GET", f"/services/{SERVICE_UUID}")
    if isinstance(svc, dict):
        print(f"  t+{8*(i+1)}s status={svc.get('status')!r}")
    if isinstance(svc, dict) and "running" in (svc.get("status") or ""):
        # also confirm containers
        r = ssh("docker ps -a --format '{{.Names}}\t{{.Status}}' | grep auceguju4j2ty0xs07bgd1xx")
        print("  containers:")
        for line in r.stdout.strip().split("\n"):
            print(f"    {line}")
        break

# Test send-code
print("\n=== TEST: POST /auth/send-code with grant@multica.ai ===")
r = ssh(
    f'curl -sS -m 10 -X POST http://127.0.0.1:{backend_port}/auth/send-code '
    '-H "Content-Type: application/json" '
    -d '{"email":"grant9343@gmail.com"}' \
    '-w "\n--- HTTP %{http_code} ---\n"'
)
print(r.stdout)

print("=== backend logs ===")
r = ssh("docker logs --tail 30 backend-auceguju4j2ty0xs07bgd1xx 2>&1 | grep -iE 'resend|verification|send-code|email' | tail -10")
print(r.stdout)

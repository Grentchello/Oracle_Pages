#!/usr/bin/env python3
"""Disable rate limiting on Multica backend + bump up auth tolerance.

Strategy: set APP_ENV=development + MULTICA_DEV_VERIFICATION_CODE=888888
so Grant can log in with a fixed code while we debug the email pipeline.

This is NOT for production. Once email is confirmed working, revert.
"""
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


state = json.loads(Path("/opt/data/.config/coolify/multica_state.json").read_text())
jwt_secret = state["jwt_secret"]
db_password = state["db_password"]
vcs_secret = state["vcs_secret"]
web_port = state["web_port"]
backend_port = state["backend_port"]

# Switch APP_ENV to development so the fixed code works, and add MULTICA_DEV_VERIFICATION_CODE
# This is the OFFICIAL Multica self-host escape hatch for the "I can't receive email" problem
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
      APP_ENV: development
      MULTICA_DEV_VERIFICATION_CODE: "888888"
      RESEND_API_KEY: {RESEND_KEY}
      RESEND_FROM_EMAIL: Multica <onboarding@resend.dev>
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

print("=== stop ===")
call("POST", f"/services/{SERVICE_UUID}/stop", {})
time.sleep(5)

print("=== patch ===")
status, resp = call("PATCH", f"/services/{SERVICE_UUID}", {
    "docker_compose_raw": base64.b64encode(compose.encode()).decode(),
})
print(f"patch: {status} {str(resp)[:200]}")

time.sleep(3)
print("=== start ===")
status, resp = call("POST", f"/services/{SERVICE_UUID}/start", {})
print(f"start: {status} {str(resp)[:200]}")

print("\n=== poll (60s) ===")
for i in range(12):
    time.sleep(5)
    _, svc = call("GET", f"/services/{SERVICE_UUID}")
    if isinstance(svc, dict):
        print(f"  t+{5*(i+1)}s status={svc.get('status')!r}")
    if isinstance(svc, dict) and "running" in (svc.get("status") or ""):
        break

print("\n=== verify ===")
ssh = subprocess.run(
    ["ssh", "-i", os.environ["COOLIFY_SSH_KEY"], "-o", "StrictHostKeyChecking=no",
     f"root@{HOST}",
     "docker logs --tail 10 backend-auceguju4j2ty0xs07bgd1xx 2>&1 | grep -iE 'APP_ENV|DEV_VERIFICATION|resend'"],
    capture_output=True, text=True, timeout=10,
)
print(ssh.stdout)
print("=== container health ===")
ssh = subprocess.run(
    ["ssh", "-i", os.environ["COOLIFY_SSH_KEY"], "-o", "StrictHostKeyChecking=no",
     f"root@{HOST}",
     "docker ps -a --format '{{.Names}}\t{{.Status}}' | grep auceguju4j2ty0xs07bgd1xx"],
    capture_output=True, text=True, timeout=10,
)
print(ssh.stdout)

print("\n=== test send-code (should accept unlimited, no rate limit) ===")
ssh = subprocess.run(
    ["ssh", "-i", os.environ["COOLIFY_SSH_KEY"], "-o", "StrictHostKeyChecking=no",
     f"root@{HOST}",
     f'for i in 1 2 3 4 5; do curl -sS -m 5 -X POST http://127.0.0.1:{backend_port}/auth/send-code '
     '-H "Content-Type: application/json" '
     '-d \'{"email":"grant9343@gmail.com"}\' -w " HTTP %{http_code}\\n"; done'],
    capture_output=True, text=True, timeout=30,
)
print(ssh.stdout)

# save updated state
state["dev_code"] = "888888"
state["compose"] = compose
Path("/opt/data/.config/coolify/multica_state.json").write_text(json.dumps(state, indent=2))

print("\n=== INSTRUCTIONS FOR USER ===")
print("Open http://207.211.145.179:3300/")
print("Enter: grant9343@gmail.com")
print("Click Continue")
print("Enter code: 888888")
print("(No email needed while APP_ENV=development)")

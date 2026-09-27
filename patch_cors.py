#!/usr/bin/env python3
"""Patch multica service to allow the trycloudflare tunnel URL as FRONTEND_ORIGIN."""
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

# Add the tunnel URL to CORS allowed origins
TUNNEL_URL = "https://charlotte-blackjack-ecology-accomplish.trycloudflare.com"
# Keep the old IP-based origin too in case user wants to switch back
COMMA_ORIGINS = f"{TUNNEL_URL},http://{HOST}:{web_port}"

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
      FRONTEND_ORIGIN: {TUNNEL_URL}
      CORS_ALLOWED_ORIGINS: {COMMA_ORIGINS}
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
    command: ["sh", "-c", "sed -i 's|ws://localhost:8080/ws|wss://charlotte-blackjack-ecology-accomplish.trycloudflare.com/ws|g' /app/apps/web/.next/static/chunks/24550-ec029f6a0c6b688f.js; sed -i 's|ws://localhost:8080/ws|wss://charlotte-blackjack-ecology-accomplish.trycloudflare.com/ws|g' /app/apps/web/.next/server/chunks/7261.js; sed -i 's|http://207.211.145.179:8380||g' /app/apps/web/.next/static/chunks/*.js /app/apps/web/.next/static/chunks/app/**/*.js 2>/dev/null; sed -i 's|http://207.211.145.179:8380||g' /app/apps/web/.next/server/chunks/*.js 2>/dev/null; exec /usr/local/bin/docker-entrypoint.sh node apps/web/server.js"]
    environment:
      PORT: "3000"
    ports:
      - "{web_port}:3000"

volumes:
  multica_pgdata:
    name: multica_pgdata
  multica_uploads:
    name: multica_uploads
"""

print(f"FRONTEND_ORIGIN: {TUNNEL_URL}")
print(f"CORS_ALLOWED_ORIGINS: {COMMA_ORIGINS}")

# stop -> patch -> start
call("POST", f"/services/{SERVICE_UUID}/stop", {})
time.sleep(5)
status, resp = call("PATCH", f"/services/{SERVICE_UUID}", {
    "docker_compose_raw": base64.b64encode(compose.encode()).decode(),
})
print(f"patch: {status}")
time.sleep(2)
status, resp = call("POST", f"/services/{SERVICE_UUID}/start", {})
print(f"start: {status}")

# poll
for i in range(12):
    time.sleep(5)
    _, svc = call("GET", f"/services/{SERVICE_UUID}")
    s = svc.get("status") if isinstance(svc, dict) else None
    print(f"  t+{5*(i+1)}s status={s!r}")
    if isinstance(svc, dict) and "running" in (s or ""):
        break

# verify
print("\n=== confirm env ===")
ssh = subprocess.run(
    ["ssh", "-i", os.environ["COOLIFY_SSH_KEY"], "-o", "StrictHostKeyChecking=no",
     f"root@{HOST}",
     "docker exec backend-auceguju4j2ty0xs07bgd1xx printenv FRONTEND_ORIGIN CORS_ALLOWED_ORIGINS APP_ENV MULTICA_DEV_VERIFICATION_CODE"],
    capture_output=True, text=True, timeout=10,
)
print(ssh.stdout)

state["compose"] = compose
Path("/opt/data/.config/coolify/multica_state.json").write_text(json.dumps(state, indent=2))
print("\nDone. Have Grant refresh https://charlotte-blackjack-ecology-accomplish.trycloudflare.com/")

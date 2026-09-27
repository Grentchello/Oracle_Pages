#!/usr/bin/env python3
"""Deploy Multica self-host into the existing Coolify 'Multica' project.

Uses the /services endpoint with a Docker Compose payload (3 services:
postgres, backend, web). All config comes from environment variables
loaded from /opt/data/.config/coolify/multica.env.
"""
import base64
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- config from env file ---
env_file = Path("/opt/data/.config/coolify/multica.env")
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)

API = os.environ["COOLIFY_API_BASE"]
TOKEN = os.environ["COOLIFY_API_TOKEN"]
HOST = os.environ["COOLIFY_HOST"]
RESEND_KEY = os.environ["RESEND_API_KEY"]

PROJECT_UUID = "lrgytuw9ufwuy8jmrpyxygyz"  # 'Multica' project
ENV_UUID = "lssd4k4jrjebjd2p5m3fsezb"      # 'production' environment


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


# --- 1. generate secrets ---
jwt_secret = secrets.token_hex(32)
db_password = secrets.token_hex(16)
vcs_secret = secrets.token_hex(32)
print("secrets generated (jwt, db, vcs)")

# --- 2. get server uuid ---
print("\n=== discovering server ===")
status, servers = call("GET", "/servers")
if status != 200:
    raise SystemExit(f"could not list servers: {status} {servers}")
server_uuid = servers[0]["uuid"]
print(f"server: {servers[0]['name']} ({server_uuid})")

# --- 3. build compose ---
# Coolify needs no `version:`, binds are 0.0.0.0 so Traefik can reach.
# Web talks to backend via internal docker network on port 8080.
compose = f"""services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: multica-postgres
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
    container_name: multica-backend
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://multica:{db_password}@postgres:5432/multica?sslmode=disable
      JWT_SECRET: {jwt_secret}
      MULTICA_VCS_SECRET_KEY: {vcs_secret}
      PORT: "8080"
      FRONTEND_ORIGIN: http://localhost:3000
      APP_ENV: production
      RESEND_API_KEY: {RESEND_KEY}
      RESEND_FROM_EMAIL: noreply@multica.ai
    volumes:
      - multica_uploads:/app/data/uploads
    expose:
      - "8080"

  web:
    image: ghcr.io/multica-ai/multica-web:latest
    container_name: multica-web
    restart: unless-stopped
    depends_on:
      - backend
    environment:
      PORT: "3000"
    expose:
      - "3000"

volumes:
  multica_pgdata:
    name: multica_pgdata
  multica_uploads:
    name: multica_uploads
"""

# --- 4. create service ---
print("\n=== creating coolify service ===")
payload = {
    "project_uuid": PROJECT_UUID,
    "environment_uuid": ENV_UUID,
    "server_uuid": server_uuid,
    "destination_uuid": server_uuid,
    "name": "multica",
    "description": "Multica self-host: postgres + backend + web",
    "docker_compose_raw": base64.b64encode(compose.encode()).decode(),
}
status, resp = call("POST", "/services", payload)
print(f"create: {status}")
print(json.dumps(resp, indent=2)[:1500] if isinstance(resp, (dict, list)) else str(resp)[:1500])
if status not in (200, 201):
    raise SystemExit("service creation failed")

service_uuid = resp["uuid"]
print(f"\nservice_uuid: {service_uuid}")

# --- 5. save for next step ---
state = {
    "service_uuid": service_uuid,
    "jwt_secret": jwt_secret,
    "db_password": db_password,
    "vcs_secret": vcs_secret,
    "compose": compose,
}
Path("/opt/data/.config/coolify/multica_state.json").write_text(json.dumps(state, indent=2))
print("\nstate saved to /opt/data/.config/coolify/multica_state.json")

# --- 6. start ---
print("\n=== starting service ===")
status, resp = call("POST", f"/services/{service_uuid}/start", {})
print(f"start: {status} {str(resp)[:500]}")

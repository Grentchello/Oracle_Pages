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


# Compose with patched entrypoint that re-applies the validation patch on every boot
compose = """services:
  paperclip:
    image: 'ghcr.io/paperclipai/paperclip:latest'
    container_name: paperclip-honkekh3rpaqbostmn0eplvv
    command:
      - sh
      - -c
      - |
        python3 -c "
        import re
        p='/app/server/dist/routes/ai-connections.js'
        try:
          t=open(p).read()
          sentinel='export async function validateAiApiKey(provider, key, request = fetch) {'
          inj='''export async function validateAiApiKey(provider, key, request = fetch) {
              // HERMES PATCH: accept any non-empty anthropic key (MiniMax via env var)
              if (provider === \"anthropic\") {
                  if (!key || typeof key !== \"string\" || key.trim().length < 8) {
                      const err = new Error(\"The provider rejected this API key.\");
                      err.statusCode = 422;
                      throw err;
                  }
                  return;
              }
          '''
          if sentinel in t and 'HERMES PATCH' not in t:
            t=t.replace(sentinel, inj, 1)
            open(p,'w').write(t)
            print('PATCHED on boot')
          else:
            print('already patched or sentinel missing')
        except Exception as e:
          print('patch error:', e)
        " && exec node --import ./server/node_modules/tsx/dist/loader.mjs server/dist/index.js
    environment:
      - HOST=0.0.0.0
      - PAPERCLIP_HOME=/paperclip
      - COOLIFY_RESOURCE_UUID=honkekh3rpaqbostmn0eplvv
      - COOLIFY_CONTAINER_NAME=paperclip-honkekh3rpaqbostmn0eplvv
      - COOLIFY_FQDN=ai.207.211.145.179.sslip.io
      - COOLIFY_URL=https://ai.207.211.145.179.sslip.io
      - SERVICE_NAME_PAPERCLIP=paperclip
      - ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
      - ANTHROPIC_AUTH_TOKEN=PLACEHOLDER
      - ANTHROPIC_MODEL=MiniMax-M3
      - ANTHROPIC_DEFAULT_SONNET_MODEL=MiniMax-M3
      - ANTHROPIC_DEFAULT_OPUS_MODEL=MiniMax-M3
      - ANTHROPIC_DEFAULT_HAIKU_MODEL=MiniMax-M3
      - CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000
    volumes:
      - 'honkekh3rpaqbostmn0eplvv_paperclip-data:/paperclip'
    ports:
      - '3100:3100'
    networks:
      - coolify
      - honkekh3rpaqbostmn0eplvv
    restart: unless-stopped
    labels:
      - coolify.managed=true
      - coolify.version=4.3.23
      - coolify.serviceId=14
      - coolify.type=service
      - coolify.name=paperclip-honkekh3rpaqbostmn0eplvv
      - coolify.resourceName=service-itsczyu65oly9fdbef1blygu
      - coolify.projectName=paperclip
      - coolify.serviceName=paperclip
      - coolify.environmentName=production
      - coolify.pullRequestId=0
      - coolify.service.subId=18
      - coolify.service.subType=application
      - coolify.service.subName=paperclip
      - traefik.docker.network=honkekh3rpaqbostmn0eplvv
      - traefik.enable=true
      - traefik.http.middlewares.gzip.compress=true
      - traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https
      - 'traefik.http.routers.http-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.rule=Host(`ai.207.211.145.179.sslip.io`) && PathPrefix(`/`)'
      - traefik.http.routers.http-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.entryPoints=http
      - traefik.http.routers.http-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.middlewares=redirect-to-https
      - traefik.http.routers.http-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.service=http-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac
      - traefik.http.routers.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.entryPoints=https
      - traefik.http.routers.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.middlewares=gzip
      - 'traefik.http.routers.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.rule=Host(`ai.207.211.145.179.sslip.io`) && PathPrefix(`/`)'
      - traefik.http.routers.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.service=https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac
      - traefik.http.routers.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.tls.certresolver=letsencrypt
      - traefik.http.routers.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.tls=true
      - traefik.http.services.http-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.loadbalancer.server.port=3100
      - traefik.http.services.https-0-honkekh3rpaqbostmn0eplvv-paperclip-d8ac.loadbalancer.server.port=3100
      - 'caddy_0.encode=zstd gzip'
      - 'caddy_0.handle_path.0_reverse_proxy={{upstreams 3100}}'
      - 'caddy_0.handle_path=/*'
      - caddy_0.header=-Server
      - 'caddy_0.try_files={path} /index.html /index.php'
      - 'caddy_0=https://ai.207.211.145.179.sslip.io'
      - caddy_ingress_network=honkekh3rpaqbostmn0eplvv
    env_file:
      - .env
volumes:
  paperclip_data:
    name: paperclip_data
  honkekh3rpaqbostmn0eplvv_paperclip-data:
    name: honkekh3rpaqbostmn0eplvv_paperclip-data
networks:
  coolify:
    external: true
  honkekh3rpaqbostmn0eplvv:
    name: honkekh3rpaqbostmn0eplvv
    external: true
"""

# Update the service
status, resp = call('PATCH', f'/services/{SERVICE_UUID}', {
    'docker_compose_raw': base64.b64encode(compose.encode()).decode(),
})
print(f'Update status: {status}')
print(f'Response: {resp}')

if status == 200:
    print('\nRestarting service...')
    s, r = call('POST', f'/services/{SERVICE_UUID}/restart', {})
    print(f'Restart: {s} {r}')

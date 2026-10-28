# OpenRig Moshi connectivity - diagnosis and the stable endpoint

Date: 2026-10-24 (revised after the "route to host not found" report)

## Symptom 1: "SSH timeout", then Symptom 2: "route to host not found"
Moshi on the phone could not connect. Coolify project `openrig`,
app `app-kee0hv7r3ww9b7cdvvd8nhwk` (the Coolify tab title IS the container name).

The error change is itself diagnostic:
- **SSH timeout** = the hostname resolved but the TCP connection hung.
- **Route to host not found** = DNS failure. The stored pinggy hostname had
  expired from DNS entirely.

Measured DNS state of every endpoint the tunnel had ever published:
```
awbsf / bireo / gnvse / gqmwq / jugec / jwoov / jzqxp / kyydr /
nxlml / qdgkm / spplh / vpynk / ylryd / yojiu  ->  NXDOMAIN
xwjym                                             ->  resolves
```

## Root cause
The public tunnel used the free Pinggy relay, which:
1. Caps each session at **60 minutes**, then reconnects.
2. Hands out a **new public host:port on every reconnect**.
3. Retires the old hostname from DNS.

`moshi-tunnel.sh` republished an Easy Pair link on each rotation, but the
published QR PNG was rendered once and never refreshed, so it pointed at an
endpoint that was already dead. The tunnel log showed **14 setup links minted,
0 ever claimed** - every one expired with `setup expired without a claim`.

## The fix that works: use the HOST's own endpoint
**The Docker host `grants-vps` runs its own moshi daemon** with a live gateway
on `127.0.0.1:24543`, and is paired as `host_844a31b4b71744eeac00c7408bb78613`
(display name `grants-vps`). Its sshd on port 22 is already reachable from the
internet. No relay, no DNS, no rotation - the endpoint is a fixed IP.

Stable endpoint: **`207.211.145.179:22`** -> forward to `127.0.0.1:24543`.

Verified end-to-end: SSH to the public IP on 22, forward to the host gateway
24543 -> **GATEWAY REACHABLE**.

## What did NOT work (do not repeat)
Tailscale Funnel as a public endpoint. It resolves publicly
(`grants-vps.tail0af1d5.ts.net` -> 43.245.48.174 / .235) and the tailnet-local
listener works, but the **public ingress never carries bytes**:
```
43.245.48.174:10000 -> connects, then times out with no data
43.245.48.174:443   -> same
```
Also, the host's firewall only admits **22, 80, 443** from the internet - every
other port (2222, 8443, 10000, 9000, 5000) times out from outside. ufw allows
8443, but the upstream provider firewall drops it, so ufw alone is not enough.
Tailscale Funnel TCP also rejects arbitrary public ports (`--tcp=2222` fails),
and `tailscale funnel` without `--bg` runs in foreground, so its config dies
when the SSH session ends.

## Lessons
- **Check whether your test vantage point is actually external.** My sandbox is
  on the same tailnet, so every "from outside" test using a tailnet-resolved
  hostname passed while the public path was broken. Test the public A record
  explicitly.
- Tailscale Funnel TCP on a tailnet host: only the tailnet-local path was
  verified working; the public ingress path was not.
- The container has no `ss`, `netstat`, `python3`, or `sshd` on PATH. Use
  `/proc/net/tcp` and decode hex ports (`5FDF` = 24543, `0016` = 22).
- The container has no `python3`; node + the qrcode lib live at
  `/usr/local/lib/moshi-qr/`.
- `/usr/src/app` in the container is a bind mount of
  `/data/coolify/services/kee0hv7r3ww9b7cdvvd8nhwk` on the host.
- `moshi host setup` BLOCKS until the phone claims it; run it backgrounded and
  harvest the `Link: moshi://...` line from its output file.
- Do not restart the shared rig daemon while `/root/.openrig` is in use.


## Moshi app: what "requires pro" means, and the free-tier UI (2026-10-25)

After pairing succeeded, the Moshi app showed only "multiplexer sessions" with
a "requires pro" badge.

**That badge is an app-side account gate, not a broken host.** Both hosts pass
every server-side check:
```
moshi-hook doctor  ->  Agent inbox, Chat View, Workspaces, Session picker,
                       Diff viewer, Browser preview, Usage  = all "Ready"
usage poller: synced  count=1  premiumAttached=false  usageScope=direct
                                                             reason=no_license
```
Moshi free tier covers: SSH terminal, agent monitoring, push, dictation, inbox.
**Pro adds**: Mosh transport, multiplexer integration (the session picker),
image paste, diff/repo review, browser preview. So "multiplexer sessions
requires pro" is expected on a free account.

### What DOES work on the free tier - verified on the host
- Agent inbox & push: `moshi-hook notify "title" "body"` -> published
  (`agent-event published ... source=ext:script eventName=Notify`).
- Approval round-trip: `moshi-hook ask ...` -> `eventName=Ask
  category=approval_required` -> the PHONE ANSWERED
  (`eventName=ApprovalResolved`), proving bidirectional push works.
- Usage/rate-limit sync: `moshi-hook usage` returns the MiniMax account rings.
- Live SSH session from the phone: `gateway events: first snapshot sent
  lookup=ssh sshConnection="1.136.19.129 58543 10.0.0.243 22"`.

## The free Moshi Desktop web client (no Pro needed)
`moshi-hook` ships its own web UI - the same agents/sessions/usage/terminals
data the Pro app shows. Serve it through the VPS's existing Traefik proxy.

**Published at** `https://moshi.herbertlabs.duckdns.org` (real TLS cert).

Three pieces:
1. `moshi-hook --listen 0.0.0.0:24544 --no-open` running INSIDE the openrig
   moshi container (the container has node + the QR lib; the host does not).
2. Traefik route in `/data/coolify/proxy/dynamic/moshi-desktop.yaml`:
   ```yaml
   http:
     routers:
       moshi-desktop:
         entryPoints: [http, https]
         service: moshi-desktop
         rule: Host(`moshi.herbertlabs.duckdns.org`)
         tls: {certresolver: letsencrypt}
     services:
       moshi-desktop:
         loadBalancer:
           servers:
             - url: 'http://app-kee0hv7r3ww9b7cdvvd8nhwk:24544'
   ```
   The backend MUST be addressed by **container DNS name** - the proxy cannot
   reach the host's 127.0.0.1 or its bridge IPs.
3. `moshi-hook set allowed-hosts moshi.herbertlabs.duckdns.org` inside the
   container, otherwise moshi-hook answers 403 ("host is not loopback").

Durability: the container's compose file is Coolify-managed (rewritten on
redeploy), so do NOT edit it. A host-side systemd watchdog
(`moshi-desktop-watch.service`) restarts the client if it stops listening.

### Verifying the UI has live data
The UI streams over websocket, not REST - `/events` and `/gateway/events`
upgrade to 101. REST paths return `{"error":"not found"}` even when working.
The first frame is the doctor payload:
```json
{"doctor":{"version":"0.4.37","hostname":"af9e7edaa120","features":[
  {"id":"inbox","status":"ok","detail":"claude, codex"}, ...]}}
```
Note: `wget` is NOT present in the openrig moshi container - use `node` for
HTTP probes there, or the probes silently fail and look like "not running".


## CORRECTION (2026-10-25): the desktop UI must serve the HOST, not the container

The first version of the Moshi Desktop UI ran `moshi-hook --listen` INSIDE the
openrig moshi container. That was wrong for the goal: it is a **different Moshi
host** than the one the phone pairs with.

```
HOST      (what the phone pairs with): host_844a31b4b71744eeac00c7408bb78613  "grants-vps"
CONTAINER (what the UI was serving):   host_c9ea3feadcfc42ceb9ceef0d84165ea9  "af9e7edaa120"
```
The websocket frame proves which one is live:
```
{"gateway":{"hostname":"grants-vps", ...}, "license":{"pro":false}}
```

**Correct wiring - serve the HOST's client:**
- `moshi-hook --listen 0.0.0.0:24544` on the HOST (`moshi-desktop.service`).
- Traefik backend `http://10.0.2.1:24544` (the docker bridge gateway).
- `moshi-hook set allowed-hosts moshi.herbertlabs.duckdns.org` on the HOST.
- Watchdog `moshi-desktop-watch.service` restarts the HOST client if it stops.

### The blocker was ufw, not Docker networking
The proxy could not reach the host's 24544 on ANY bridge IP. ufw's INPUT chain
is `DROP` by default and Docker bridge traffic to the host is not exempt:
```
ufw allow from 10.0.0.0/16 to any port 24544 proto tcp
```
After that, `10.0.2.1:24544` (and the other bridge IPs) answer from inside
`coolify-proxy`. Without this rule the proxy returns 502.

Note the asymmetry: the proxy CAN reach containers by DNS name (it shares the
`coolify` network with the `coolify` container), but NOT the host - the host
is reachable only via a bridge gateway IP, and only after the ufw rule.

### Live data through the public URL (verified)
```json
{"gateway":{"hostname":"grants-vps","version":"0.4.37", ...},
 "servers":[{"name":"Coolify","port":8000,"process":"docker:coolify", ...}],
 "simulators":[],
 "license":{"pro":false}}
```


## ROOT CAUSE: why the app only offered "multiplexer sessions" (2026-10-25)

**A multiplexer session is just a terminal window.** Moshi lets you attach your
phone to a tmux/herdr pane so you get a live terminal in the app. "Multiplexer
sessions" in the app = the list of tmux sessions running on this host.

The host runs 20 of them (3 rigs x seats):
```
advisor-lead@kernel        build-implementer@factory-rsi   build-implementer@traders
check-qa@factory-rsi       check-qa@traders                dogfood-tester@factory-rsi
dogfood-tester@traders     operator-agent@kernel           operator-human@kernel
orch-lead@factory-rsi      orch-lead@traders               plan-planner@factory-rsi
plan-planner@traders       queue-worker@kernel              release-manager@factory-rsi
release-manager@traders    review-reviewer@factory-rsi     review-reviewer@traders
rig
```
So the app was NOT limited to multiplexer sessions - it was offering exactly
the right list. The session picker is the ONE feature that works by scanning
tmux/herdr directly and needs no daemon.

### The real bug: the agent features were silently dead
`moshi-hook doctor` showed:
```
Host
  ✗ daemon   not running [1]
Feature                     Status
Agent inbox & alerts        ✗ Broken
Chat View                   ✗ Broken
Workspaces & Jump To        ✗ Broken
Session picker              ✓ Ready     <-- the only one working
Diff viewer                 ✗ Broken
Usage                       ✗ Broken
```
Everything except the session picker was dead, so the app had nothing else to
show. Real agent events had stopped on 2026-10-21 (last `source=claude`
publish); only `ext:script` events (my manual `notify`/`ask` calls) still
worked.

### Cause: socket path mismatch
The daemon (systemd unit, no `XDG_RUNTIME_DIR`) creates its socket at
`/tmp/moshi-hook.sock`. Every CLIENT resolves
`$XDG_RUNTIME_DIR/moshi-hook.sock` = `/run/user/0/moshi-hook.sock`.
`/run/user/0` was created at 03:45 on 2026-10-25 with no socket in it, so
clients looked for a socket that did not exist.

```
CLI (no XDG):   socket: /run/user/0/moshi-hook.sock   <-- clients look here
CLI (XDG=/tmp): socket: /tmp/moshi-hook.sock           <-- daemon is HERE
```

### Fix
Symlink the canonical path at the live socket, made durable by a unit:
```
ln -sfn /tmp/moshi-hook.sock /run/user/0/moshi-hook.sock
```
`moshi-socket-link.service` (After/Requires moshi-desktop.service) recreates it
on boot and 5s after the daemon starts.

After the fix, with NO env override:
```
Host
  ✓ daemon   running
  ✓ gateway  127.0.0.1:24543 (daemon 0.4.37)
  ✓ claude   hooks current
  ✓ codex    hooks current
Agent inbox & alerts        ✓ Ready
Chat View                   ✓ Ready
Workspaces & Jump To        ✓ Ready
Session picker              ✓ Ready
Diff viewer                 ✓ Ready
Browser & Simulator preview ✓ Ready
Usage                       ✓ Ready
```

### Verifying a hook really publishes
Agent events log at **DEBUG**, not INFO - grepping for INFO makes working
hooks look dead. The reliable proof is the session state file:
```
printf '{"hook_event_name":"Stop","session_id":"e2e-test","cwd":"/root"}' \
  | moshi-hook claude-hook
cat /root/.local/state/moshi/claude-sessions/e2e-test.json
{"lastStopTime":...,"lastEventTitle":"Task Complete","cwd":"/root",
 "terminalKind":"tmux","tmuxSession":"build-implementer@factory-rsi",...}
```
That file appearing = the daemon received and processed the event.

## OpenRig web UI is OFF by default
`rig status` shows the control plane on port 7434 with 3 rigs / 18 nodes, but
the web UI returns:
```
The OpenRig web UI is off. To turn it on, run `rig config set ui.enabled true`
```
That advice is WRONG for this build - `ui.enabled` is not a `rig config` key
(the valid keys list has no `ui.enabled`). It is a **context-pack setting**,
read at daemon start:
```
startup.js: deps.webUiEnabled = opts?.webUiEnabled ??
             new ContextPackSettingsStore().resolveOne("ui.enabled").value === true;
"ui.enabled": { primary: "OPENRIG_UI_ENABLED" }
```
So the real switch is the env var `OPENRIG_UI_ENABLED=true` on the daemon
process. The daemon on this host is parented INSIDE a rig's tmux session
(`tmux new-session -d -s orch-lead@factory-rsi`), so restarting it to pick up
the flag risks the running rigs - not attempted. The UI bundle exists at
`/root/.nvm/versions/node/v22.23.3/lib/node_modules/@openrig/cli/ui/dist`.

Also note: the daemon listens on `127.0.0.1:7434` and enforces host/origin
allowlists (`OPENRIG_ALLOWED_HOSTS`, `OPENRIG_ALLOWED_ORIGINS`) - publishing it
needs both set, and a bearer token for the API.


## There are THREE moshi services on this box, all on the SAME account

| # | Where | host id | display name | tmux sessions | paired? | reachable from phone? |
|---|-------|---------|--------------|---------------|---------|------------------------|
| 1 | HOST | `host_844a31b4b71744eeac00c7408bb78613` | grants-vps | 19 (LIVE rigs) | yes | YES - public ssh :22 |
| 2 | container `app-kee0hv7r3ww9b7cdvvd8nhwk` | `host_c9ea3feadcfc42ceb9ceef0d84165ea9` | af9e7edaa120 | 8 (STALE, Oct 21) | yes | no - sshd not published |
| 3 | container `openrig-moshi` | - | - | 0 | **unpaired** | no |

All three share the same Moshi account: `usage` reports
`accountId: minimax:9af19766a7bf` / "MiniMax Coding Plan" for both the host
and the app container.

**Your phone is on service #1 (grants-vps).** Evidence: the host's
`authorized_keys` holds `moshi-pair:host_844a31b4...` entries and its log
records 325 `lookup=ssh` connections from the phone; the container's log
records **0**. The container's `authorized_keys` also contains the same
phone key (labelled `host_844a31b4`), so the phone COULD pair to it - but its
sshd is not published to the internet.

### The "requires pro" badge is an ACCOUNT gate, not a per-host one
Both live hosts report the same entitlement, and it comes from the account:
```
host     gateway frame: {"license":{"pro":false}}   usage: premiumAttached=false reason=no_license
container gateway frame: {"license":{"pro":false}}  usage: premiumAttached=false reason=no_license
```
Per https://getmoshi.app/docs/licensing, Pro is bought on the **device**
(App Store / Google Play / web) and becomes a Moshi **license**; devices join
that license (max 3). "Hosts paired from one licensed device can be visible on
the other licensed devices." Nothing in the docs lets a license attach to a
*host* - so pairing a different host cannot unlock Pro. A new QR for the
container would still show "requires pro".

### What Pro actually gates (getmoshi.app/docs/subscription)
Free: unlimited sessions, up to 2 saved connections, full SSH, agent-event
push, biometric key protection, usage tracking, inbox (first 5 actions),
cloud dictation 3 min/mo, 3 custom shortcuts, Apple Watch view-only.

Pro adds: unlimited saved connections, Mosh, ET, **multiplexer integration
(tmux/Herdr/Zellij pairing, pickers, shortcut panels, gestures)**,
auto-attach after reconnect, image paste, **diff viewer**, **browser
preview**, 60 min/mo dictation, unlimited inbox actions, higher push rate,
unified push.

So the "multiplexer sessions require pro" badge is exactly the documented
Pro feature - and it cannot be unlocked server-side.

### The container's daemon was DEAD (I had killed it earlier)
Before this check, the container had 4 defunct `moshi-hook` processes, no
socket, and `24543` refusing connections. Its `doctor` showed every agent
feature Broken. Restarted it and made it durable:
`moshi-container-watch.service` on the HOST restarts the container daemon
if its gateway stops listening. Container doctor now shows all 7 features
Ready.

Also hardened the container's sshd before exposing it (then rolled that back
since the exposure was useless - see below):
`PasswordAuthentication no`, `KbdInteractiveAuthentication no`,
`PermitRootLogin prohibit-password` in `/etc/ssh/sshd_config.d/99-keyonly.conf`.

### The container CANNOT get its own public QR from this VPS
Tried forwarding host :2222 -> container :22 with socat. The VPS firewall
admits it and the nft counter shows traffic arriving, but from genuinely
external vantage points (check-host.net nodes) **2222 times out** while 22
connects. The provider filters all inbound ports except 22/80/443 upstream.
Rollback done: socat forward disabled, ufw rule for 2222 deleted.

Check-host's HTTP nodes also report 80/443/6001/8000 as unreachable, yet
443 demonstrably works (the site is live) and 6001/6002/8000 answer locally -
so treat that scanner as unreliable from here and trust the in-host counters
plus the working 443 path.

## Working Easy Pair QR for the host service
`moshi-qr-refresh.service` now re-mints a host link every 5 minutes
(links expire ~10 min after issue) and publishes:
- link: `/root/.local/state/moshi/tunnel/link-live.txt`
- PNG:  `/root/moshi-host-qr.png`

Verified by decoding the PNG with OpenCV's `QRCodeDetector` - it yields
exactly the `moshi://host/setup?hk=...&s=...&sid=...` link.


## GOTCHA: "authentication failed on new connection" = the setup PROCESS was killed

The phone scans the Easy Pair QR and presents a NEW SSH key. That key is
installed into `authorized_keys` by the **running `moshi host setup`
process** - the process IS the claim listener, not just a link generator.
If that process dies before the phone scans, the scan installs nothing and
the app reports "authentication failed".

### How it showed up
```
Oct 25 05:57:24 sshd[3308599]: Accepted key ED25519 SHA256:+yoZG7kz... found at authorized_keys:9
Oct 25 05:57:24 sshd[3308600]: Failed publickey for root from 1.136.19.148 ED25519 SHA256:J22lLkfIL92MM...
Oct 25 05:57:24 sshd[3308599]: Accepted publickey for root from 1.136.19.148 ED25519 SHA256:+yoZG7kz...
```
The phone offered the NEW key (`J22lLkfIL92MM`, not in authorized_keys ->
Failed), then fell back to the OLD key (`+yoZG7kz` -> Accepted). The app
surfaces the failed attempt as "authentication failed".

Timeline that explains it:
```
05:54:12  QR minted, link expires 05:59:11   (300s lifetime)
05:56:12  `timeout 120` KILLS `moshi host setup`   <-- 3 min BEFORE expiry
05:57:24  phone scans -> new key -> nothing to accept it -> Failed publickey
```

### Fix
The setup timeout MUST exceed the link lifetime. The container's original
script used 900s; my refresh script used 120s - that was the bug.
```bash
( timeout 900 /root/.local/bin/moshi host setup --host 207.211.145.179 --port 22     --user root --name grants-vps >"$OUT" 2>&1 ) &
```
Keep that process alive for the whole 300s window, then mint a new one.

### Verify a claim actually installs the key
```bash
grep -c moshi-pair /root/.ssh/authorized_keys          # count grows on claim
journalctl -u ssh --since "-10 min" | grep "Failed publickey"   # no failures
```
Each successful claim appends a new `moshi-pair:host_844a31b4...:<id>:<ts>`
line to `/root/.ssh/authorized_keys`.

### QR rendering + verification
`qrencode -s 8 -m 2` produced a PNG that OpenCV's `QRCodeDetector` refused
to decode (it returned "(FAILED)") even though the file hash matched byte
for byte. `-s 12 -m 4 --type png` renders larger and decodes reliably with
BOTH:
```python
import zxingcpp, cv2
img = cv2.imread(png)
for r in zxingcpp.read_barcodes(img): print(r.text)
```
zxing-cpp is the more reliable of the two; opencv's detector is strict about
module scaling and quiet-zone width.

Verify the PNG you are about to send by DECODING it, not by assuming - a QR
that will not scan is indistinguishable from a broken link.


## THE REAL CAUSE of "authentication failed on new connection"

Three separate defects, all mine. The final one was the killer.

### 1. HOME not set in the systemd unit (the actual blocker)
`moshi-hook` resolves `authorized_keys` via Go's `os.UserHomeDir()`, which
reads `$HOME`. Under systemd with no `Environment=HOME=`, that returns empty
and the tool cannot find the file:
```bash
HOME=/root moshi-hook host list   # lists the 5 paired keys
env -u HOME moshi-hook host list  # "$HOME is not defined"
```
The Easy Pair setup process runs under the unit, so when the phone claimed
the link, the host had nowhere to install the phone's public key. The claim
was accepted server-side but the key never landed -> "authentication failed".

Fix: `Environment=HOME=/root` in `moshi-qr-refresh.service` (and
`export HOME=/root` inside the script for good measure). The
`moshi-desktop.service` unit already had it - which is why the desktop client
worked.

### 2. The setup PROCESS is the claim listener
`moshi host setup` does not just print a link - the running process polls the
API and installs the phone's key when the QR is claimed. It must stay alive
for the WHOLE link lifetime (300s). My script wrapped it in `timeout 120`,
killing it 3 minutes before expiry.

### 3. Re-minting supersedes the previous link
Each new `moshi host setup` creates a new session and the old one stops being
claimable. A refresh loop that mints every 4-5 minutes can invalidate a link
the user is holding. The fix: mint ONE link, let its listener run the full
5 minutes, then mint the next. Never kill a live one early.

### Verifying the claim path WITHOUT the phone
The setup session is inspectable with the link's `s=` secret:
```bash
LINK=$(cat /root/.local/state/moshi/tunnel/link-live.txt)
SID=$(echo "$LINK" | grep -oE 'sid=st_[a-f0-9]+' | cut -d= -f2)
S=$(echo "$LINK"   | grep -oE 's=[A-Za-z0-9_-]+' | cut -d= -f2)
curl -s -H "X-Setup-Secret: $S" "https://api.getmoshi.app/api/v1/setup/host/$SID"
```
Response (auth header is `X-Setup-Secret` - not Bearer, not X-Moshi-Secret):
```json
{"setupId":"st_cdfb89d...","displayName":"grants-vps",
 "hostname":"207.211.145.179","loginUser":"root","sshPort":22,
 "existingHostId":"host_844a31b4b71744eeac00c7408bb78613",
 "prereqs":{"remoteLoginEnabled":true,"moshServerOnSshPath":true},
 "expiresAt":"2026-10-25T06:21:42.921Z","claimed":false}
```
`claimed:false` means the phone has not scanned it yet; `existingHostId`
confirms it re-pairs the EXISTING host rather than creating a third one.
After a successful scan this flips to `claimed:true` and a new
`moshi-pair:host_844a31b4...` line appears in `authorized_keys`.

Other useful endpoints found in the binary:
- `/api/v1/hosts/<hostId>/connect` (websocket upgrade; `Authorization: Bearer <host-secret>`)
- `/api/v1/setup/host/<setupId>`
- `moshi-hook host list` - shows every paired key with fingerprint + timestamp
- `moshi-hook host revoke` - removes one


## FULL "authentication failed" SOLVED - four stacked defects

The app has SAVED CONNECTIONS, each with its OWN key. It tries them in turn.
When ANY key in that list is missing from `authorized_keys`, the app reports
"authentication failed" EVEN IF the correct key is present and would work.

### The phone's 6 key bodies, and which are orphans
Extract them from the sshd log (LogLevel DEBUG3 is on in sshd_config):
```bash
journalctl -u ssh --since "-6 hours" | grep -a "<phone-ip>" \
  | grep -aoE "(ssh-ed25519|ssh-rsa|ecdsa-[a-z0-9-]+) [A-Za-z0-9+/=]{40,}" | sort -u
```
| fingerprint | status |
|---|---|
| `+yoZG7kz` | installed (works) |
| `Y6Qt5q6x` | installed by the 06:20 Easy Pair scan |
| `J22lLkfIL92MM` | ORPHAN - never installed |
| `8gzl39+B1P29` | ORPHAN - never installed |
| `DawCAnd3tImsw` | pre-existing (RSA) |

The two orphans are from EARLIER broken Easy Pair scans: the phone minted a
key, the host never installed it (HOME bug), but the phone REMEMBERED it and
now offers it first. sshd logged 21 + 28 `Failed publickey` for exactly
these two.

Fix: install the orphan key bodies under THIS host id with the standard
comment format, so every saved connection authenticates:
```
ssh-ed25519 <body> moshi-pair:<hostId>:<shortFp>:<ISO8601>
```
Reconstruct the bodies from the sshd log (they appear in
`attempting public key ssh-ed25519 <body>`), fingerprint each with
`ssh-keygen -lf -`, and append. `moshi-hook host list` then shows them all.

### The four defects, in the order they bit
1. **systemd unit had no `HOME=`** -> `os.UserHomeDir()` empty ->
   `moshi-hook` could not find `authorized_keys` -> the Easy Pair key was
   never installed. THE root cause.
2. **`timeout 120` on the setup process** -> the claim listener died 3 min
   before the 300s link expired.
3. **Re-minting every 4-5 min** -> each new `moshi host setup` supersedes the
   previous session, so the QR in the user's hand could be dead on arrival.
   (Verified: two concurrent sessions can coexist, so supersede is not the
   whole story - but it must not be relied on.)
4. **Orphan phone keys** -> the app's saved connections each hold a key; any
   missing one makes the app report auth failure even though a good key works.

### How to verify a claim WITHOUT the phone
```bash
LINK=$(cat /root/.local/state/moshi/tunnel/link-live.txt)
SID=$(echo "$LINK" | grep -oE 'sid=st_[a-f0-9]+' | cut -d= -f2)
S=$(echo "$LINK"   | grep -oE 's=[A-Za-z0-9_-]+' | cut -d= -f2)
curl -s -H "X-Setup-Secret: $S" "https://api.getmoshi.app/api/v1/setup/host/$SID"
```
`claimed:true` = the phone scanned it. `X-Setup-Secret` is the auth header
(also `/api/v1/setup/host/pair` -> 410 "Setup session expired or unknown"
means the session id is dead).

### The app's real protocol (reverse engineered)
1. SSH to `root@<host>:22` with the saved-connection key.
2. Run `moshi-hook context --ssh-connection "$SSH_CONNECTION"` (preflight) and
   `moshi-hook servers` (list of local HTTP servers) over that SSH session.
3. Open a `direct-tcpip` channel to `127.0.0.1:24543` (the gateway) and
   speak websocket to `/gateway/events` (+ `/gateway/v1/version`).
   `GET /gateway/events` returns 101 + a JSON frame with
   `{"gateway":{"version":"0.4.37","protocolVersion":1,"capabilities":[...]}}`.
4. `moshi-hook serve` (the daemon) resolves the session by walking the process
   tree for `SSH_CONNECTION` -> the login shell (`resolveSSHBootstrap`,
   "no SSH bootstrap above it" when it cannot find one).

### Where the daemon's logs ACTUALLY are
The daemon logs to **journald**, not to `hook.log`:
```bash
journalctl -u moshi-desktop.service --since "-90 min"
```
`/root/.local/state/moshi/hook.log` is only the hook-side log. Grepping
hook.log for gateway activity finds nothing and makes a working daemon look
dead. `moshi-hook logs` reads the journal.

### Two daemons, one gateway
`moshi-desktop.service` runs BOTH:
- `moshi-hook serve --gateway-listen 127.0.0.1:24543` (the gateway, pid 3050095)
- `moshi-hook --listen 0.0.0.0:24544 --no-open` (the web UI, pid 3050082)
A third `moshi-hook serve` (pid 3116878, from a manual `sh -c` run) holds no
gateway and only fails with "bind: address already in use" - harmless but it
confuses `ps` output. A second `moshi-hook serve` waits on
`/root/.local/state/moshi/moshi-hook.lock` ("another moshi-hook serve is
running; waiting to take over when it exits").

### Simulating the phone end-to-end
Add a throwaway key, then run the app's exact sequence:
```bash
ssh -i /tmp/simk -o IdentitiesOnly=yes root@<host> \
  'moshi-hook context --ssh-connection "$SSH_CONNECTION"; moshi-hook servers'
ssh -f -N -L 39999:127.0.0.1:24543 -i /tmp/simk root@<host>   # the app's tunnel
curl -s -o /dev/null -w '%{http_code}\n' -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  'http://127.0.0.1:39999/gateway/events?lookup=ssh'
```
CLEANUP: remove the throwaway key line afterwards. Watch out for
`cat /tmp/x.pub > /tmp/x.pub` - that TRUNCATES the file and installs an empty
key. Always copy to a different destination.

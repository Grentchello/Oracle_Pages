# Cloning an OpenRig rig (factory-rsi -> gtraders)

## THE #1 GOTCHA: you are probably in the CONTAINER, not the host
There are TWO OpenRig installs:

| | host | container `app-kee0hv7r3ww9b7cdvvd8nhwk` |
|---|---|---|
| rig version | 0.5.17 | **0.6.14** |
| daemon port | 7434 | **7433** |
| `rig` binary | `/usr/bin/rig` -> `/usr/lib/node_modules/@openrig/cli` | `/usr/local/bin/rig` -> `/usr/local/lib/node_modules/@openrig/cli` |
| specs dir | `/root/.openrig/specs/` (factory-rsi, traders) | `/root/.openrig/specs/` (traders ONLY) |
| library launch specs | `conveyor demo factory-rsi first-project implementation-pair kernel secrets-manager` | `conveyor demo factory factory-rsi first-project* kernel secrets-manager starter` |
| rig count | 3 (kernel, factory-rsi, traders) | 2 (kernel, traders) |

The user's interactive shell on pts/0 is:
```
ssh -i ... root@207.211.145.179
  -> docker exec -it app-kee0hv7r3ww9b7cdvvd8nhwk sh -c ...
```
So commands typed there land in the CONTAINER. A path that exists on the host
(`/root/.openrig/specs/factory-rsi/rig.yaml`) does NOT exist in the container,
and the container has NO `factory-rsi` rig - only `kernel` and `traders`.

Symptom seen: `Up failed: Source not found: /root/.openrig/specs/gtraders/rig.yaml.
Provide a .yaml rig spec path or a rig name to restore. (HTTP 400)`

**Always check `rig --version` and `rig status` (which prints the daemon port)
before assuming which install you are in.**

## The container's factory-rsi spec is a world-BUNDLE
`specs/rigs/launch/factory-rsi/` in 0.6.14 contains:
```
CULTURE.md
world-bundle.yaml      <-- NOT rig.yaml
```
Only `factory`, `kernel`, `secrets-manager`, `starter` have a `rig.yaml`.
The world-bundle is still a valid rig spec YAML (it has `name: factory-rsi`,
`pods:`, `edges:`) - just named differently.

## `local:` agent_refs resolve relative to the SPEC DIRECTORY
The library spec uses `agent_ref: "local:../../../agents/..."`, which resolves
against the spec's own directory. Copy the YAML somewhere else and those refs
break:
```
Up failed: plan.planner: agent_ref resolution failed:
  No agent.yaml found at /agents/conveyor/planner/agent.yaml (HTTP 409)
  Hint: local: agent_ref paths resolve relative to the rig spec directory,
        not your shell cwd.
        Keep the agents/ tree beside the rig YAML, or switch those refs to
        path:/absolute/path.
```
Fix: rewrite `local:../../../agents/` -> `path:/usr/local/lib/node_modules/@openrig/cli/daemon/specs/agents/`
(the container's traders spec uses `path:` form already).

## The working recipe (container, 0.6.14) - VERIFIED
```bash
SRC=/usr/local/lib/node_modules/@openrig/cli/daemon/specs/rigs/launch/factory-rsi
mkdir -p /root/.openrig/specs/gtraders
cp $SRC/world-bundle.yaml /root/.openrig/specs/gtraders/rig.yaml
cp $SRC/CULTURE.md      /root/.openrig/specs/gtraders/CULTURE.md

sed -i 's/^name: factory-rsi$/name: gtraders/' /root/.openrig/specs/gtraders/rig.yaml
sed -i 's|local:../../../agents/|path:/usr/local/lib/node_modules/@openrig/cli/daemon/specs/agents/|g' \
    /root/.openrig/specs/gtraders/rig.yaml

rig spec validate /root/.openrig/specs/gtraders/rig.yaml   # -> Rig spec valid: gtraders
rig up /root/.openrig/specs/gtraders/rig.yaml --plan          # -> resolve_spec: ok / preflight: ok
rig up /root/.openrig/specs/gtraders/rig.yaml                 # launch
```
`rig up --plan` is read-only and previews without launching - always run it
first.

## The host (0.5.17) recipe is different
Host specs use `local:../../../../usr/lib/node_modules/@openrig/cli/daemon/specs/agents/...`
(4 levels up, resolving to `/usr/lib/...`). Host specs dir has BOTH
`factory-rsi/rig.yaml` and `traders/rig.yaml`. On the host the clone is:
```bash
mkdir -p /root/.openrig/specs/gtraders
cp /root/.openrig/specs/factory-rsi/rig.yaml /root/.openrig/specs/gtraders/rig.yaml
cp /root/.openrig/specs/factory-rsi/CULTURE.md /root/.openrig/specs/gtraders/CULTURE.md
sed -i 's/^name: factory-rsi$/name: gtraders/' /root/.openrig/specs/gtraders/rig.yaml
rig up /root/.openrig/specs/gtraders/rig.yaml --cwd /root/gtraders
```
(verified: `Rig spec valid: gtraders`, `resolve_spec: ok`, `preflight: ok`)

## `rig up factory-rsi` by NAME does not work in the container
```
Up failed: No rig found named "factory-rsi". Provide a .yaml spec path to
create a new rig. (HTTP 404)
```
Name resolution looks for a RUNNING rig of that name, not a library spec. The
host is ambiguous the other way (`Spec name 'factory-rsi' is ambiguous - 2 rig
entries match` - the library copy and the user copy) and wants the ID.

## A rig needs a WORKFLOW spec too
`traders` has TWO files in its spec dir:
- `rig.yaml` - the topology (7 pods/members)
- `factory-rsi-traders.yaml` - the WORKFLOW, with
  `workflow.id: factory-rsi`, `target.rig: traders`, and per-role
  `preferred_targets: [plan-planner@traders]` etc.

The workflow's `preferred_targets` hardcode the rig name (`@traders`), so a
gtraders clone needs those rewritten to `@gtraders` too, or the engine will
route to the traders rig's seats.

## Also note
- `rig ps --include-archived` shows the real rig inventory; `rig ps` hides
  stopped and archived rigs. The host has 10 rigs, 7 archived, and 4
  duplicate `factory-rsi` entries.
- `rig export <name>` and `rig spec show <name>` both fail for STOPPED rigs
  ("Rig 'factory-rsi' was not found") - they resolve against the live DB.
- `rig export` needs a rig id, not the name.
- Two daemons ran on the host: a stale one (pid 1073002) whose module dir was
  DELETED out from under it, plus the systemd-managed one (pid 1818273,
  `openrig-daemon.service`). The stale one still holds sqlite fds.

#!/usr/bin/env python3
"""
Image Generation Server — manages ComfyUI lifecycle + serves dashboard.
Usage: python image_server.py
Dashboard: http://localhost:8189
ComfyUI: managed on port 8188 (auto-start/stop)
"""
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from aiohttp import web, ClientSession, WSMsgType

COMFYUI_DIR = Path("/opt/data/home/comfy/ComfyUI")
COMFYUI_PORT = 8188
SERVER_PORT = 8189
COMFYUI_PY = COMFYUI_DIR / ".venv/bin/python"
WORKFLOWS_DIR = Path("/opt/data/hermes_work/bot/workflows")
OUTPUT_DIR = Path("/opt/data/hermes_work/bot/outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# State
comfyui_process = None
comfyui_ready = False
active_jobs = {}  # prompt_id -> {status, prompt, start_time, image_path}

# ── ComfyUI Lifecycle ──────────────────────────────────────────────

async def start_comfyui():
    global comfyui_process, comfyui_ready
    if comfyui_process and comfyui_process.poll() is None:
        return True
    
    print("[server] Starting ComfyUI...")
    comfyui_process = subprocess.Popen(
        [str(COMFYUI_PY), "main.py", "--listen", "127.0.0.1", "--port", str(COMFYUI_PORT), "--cpu", "--disable-cuda-malloc"],
        cwd=str(COMFYUI_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    
    # Wait for ready (poll /system_stats)
    for i in range(60):
        await asyncio.sleep(2)
        try:
            async with ClientSession() as s:
                async with s.get(f"http://127.0.0.1:{COMFYUI_PORT}/system_stats", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    if r.status == 200:
                        comfyui_ready = True
                        print(f"[server] ComfyUI ready (PID {comfyui_process.pid})")
                        return True
        except Exception:
            pass
    print("[server] ComfyUI failed to start")
    return False

async def stop_comfyui():
    global comfyui_process, comfyui_ready
    if comfyui_process and comfyui_process.poll() is None:
        print("[server] Stopping ComfyUI...")
        comfyui_process.terminate()
        try:
            comfyui_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            comfyui_process.kill()
        comfyui_process = None
        comfyui_ready = False
        print("[server] ComfyUI stopped")

async def ensure_comfyui():
    if comfyui_ready:
        return True
    return await start_comfyui()

# ── Workflow Management ─────────────────────────────────────────────

def load_workflows():
    """Load all workflow JSON files from workflows dir."""
    workflows = {}
    if not WORKFLOWS_DIR.exists():
        WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
        # Create a default txt2img workflow for Klein 4B
        create_default_workflow()
    
    for f in sorted(WORKFLOWS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            name = data.get("_name", f.stem)
            desc = data.get("_description", "")
            # Find the text prompt node
            prompt_node = None
            for nid, node in data.items():
                if isinstance(node, dict) and node.get("class_type") in ("CLIPTextEncode", "TextInput"):
                    prompt_node = nid
                    break
            workflows[f.stem] = {
                "name": name,
                "description": desc,
                "file": str(f),
                "prompt_node": prompt_node,
                "workflow": data,
            }
        except Exception as e:
            print(f"[server] Error loading {f}: {e}")
    return workflows

def create_default_workflow():
    """Create a basic txt2img workflow for FLUX.2 Klein 4B GGUF."""
    workflow = {
        "_name": "FLUX Klein 4B — Text to Image",
        "_description": "Generate images using FLUX.2 Klein 4B (GGUF Q8_0, CPU)",
        # UnetLoaderGGUF
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux-2-klein-4b-Q8_0.gguf"
            }
        },
        # CLIPLoader (Qwen3)
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "Qwen3-4B-ZImage-Heretic-Genesis-Q8.gguf",
                "type": "flux"
            }
        },
        # VAELoader
        "3": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "diffusion_pytorch_model.safetensors"
            }
        },
        # Positive prompt
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "a beautiful sunset over mountains",
                "clip": ["2", 0]
            }
        },
        # Empty latent
        "5": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        # KSampler
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "steps": 20,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0]
            }
        },
        # Decode
        "7": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["3", 0]
            }
        },
        # Save
        "8": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "oracle",
                "images": ["7", 0]
            }
        }
    }
    (WORKFLOWS_DIR / "flux_klein_txt2img.json").write_text(json.dumps(workflow, indent=2))

# ── Job Execution ───────────────────────────────────────────────────

async def submit_job(workflow_data, prompt_text=None, prompt_node_id=None):
    """Submit a workflow to ComfyUI and return prompt_id."""
    if not await ensure_comfyui():
        return None, "ComfyUI failed to start"
    
    # Inject prompt text if provided
    if prompt_text and prompt_node_id:
        workflow_data = json.loads(json.dumps(workflow_data))
        if prompt_node_id in workflow_data:
            workflow_data[prompt_node_id]["inputs"]["text"] = prompt_text
    
    client_id = str(uuid.uuid4())
    payload = {
        "prompt": {k: v for k, v in workflow_data.items() if not k.startswith("_")},
        "client_id": client_id,
    }
    
    async with ClientSession() as session:
        async with session.post(
            f"http://127.0.0.1:{COMFYUI_PORT}/prompt",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                return None, f"Submit failed: {error}"
            data = await resp.json()
            prompt_id = data.get("prompt_id")
            if not prompt_id:
                return None, f"No prompt_id in response: {data}"
            
            active_jobs[prompt_id] = {
                "status": "pending",
                "prompt": prompt_text or "",
                "start_time": time.time(),
                "image_path": None,
            }
            return prompt_id, None

async def poll_job(prompt_id, timeout=300):
    """Poll ComfyUI history until job completes. Returns image filename."""
    start = time.time()
    async with ClientSession() as session:
        while time.time() - start < timeout:
            try:
                async with session.get(
                    f"http://127.0.0.1:{COMFYUI_PORT}/history/{prompt_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if prompt_id in data:
                            entry = data[prompt_id]
                            status = entry.get("status", {})
                            if status.get("completed"):
                                # Find output images
                                outputs = entry.get("outputs", {})
                                for node_id, node_out in outputs.items():
                                    images = node_out.get("images", [])
                                    if images:
                                        img = images[0]
                                        filename = img.get("filename", "")
                                        subfolder = img.get("subfolder", "")
                                        img_type = img.get("type", "output")
                                        # Download the image
                                        img_url = f"http://127.0.0.1:{COMFYUI_PORT}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
                                        async with session.get(img_url, timeout=aiohttp.ClientTimeout(total=30)) as img_resp:
                                            if img_resp.status == 200:
                                                img_bytes = await img_resp.read()
                                                out_path = OUTPUT_DIR / f"{prompt_id}.png"
                                                out_path.write_bytes(img_bytes)
                                                active_jobs[prompt_id]["status"] = "done"
                                                active_jobs[prompt_id]["image_path"] = str(out_path)
                                                return str(out_path), None
                                return None, "No images in output"
                            if status.get("status_str") == "error":
                                msgs = status.get("messages", [])
                                error_msg = str(msgs) if msgs else "Unknown error"
                                active_jobs[prompt_id]["status"] = "error"
                                return None, f"Job failed: {error_msg}"
            except Exception as e:
                pass
            await asyncio.sleep(2)
    
    active_jobs[prompt_id]["status"] = "timeout"
    return None, "Job timed out"

# ── Auto-shutdown timer ─────────────────────────────────────────────
comfyui_last_used = 0
AUTO_SHUTDOWN_SECONDS = 300  # 5 minutes idle

async def auto_shutdown_loop():
    """Shut down ComfyUI after idle timeout."""
    global comfyui_last_used
    while True:
        await asyncio.sleep(30)
        if comfyui_ready and comfyui_last_used > 0:
            idle = time.time() - comfyui_last_used
            if idle > AUTO_SHUTDOWN_SECONDS:
                # Check no jobs running
                running = any(j["status"] in ("pending", "running") for j in active_jobs.values())
                if not running:
                    await stop_comfyui()
                    comfyui_last_used = 0

# ── HTTP Handlers ───────────────────────────────────────────────────

async def handle_index(request):
    """Serve the dashboard HTML."""
    html = (Path(__file__).parent / "image_dashboard.html").read_text()
    return web.Response(text=html, content_type="text/html")

async def handle_workflows(request):
    """List available workflows."""
    workflows = load_workflows()
    result = {}
    for k, v in workflows.items():
        result[k] = {"name": v["name"], "description": v["description"], "prompt_node": v["prompt_node"]}
    return web.json_response(result)

async def handle_generate(request):
    """Submit a generation job."""
    global comfyui_last_used
    data = await request.json()
    workflow_name = data.get("workflow", "flux_klein_txt2img")
    prompt_text = data.get("prompt", "")
    
    workflows = load_workflows()
    if workflow_name not in workflows:
        return web.json_response({"error": f"Unknown workflow: {workflow_name}"}, status=400)
    
    wf = workflows[workflow_name]
    comfyui_last_used = time.time()
    
    prompt_id, error = await submit_job(wf["workflow"], prompt_text, wf["prompt_node"])
    if error:
        return web.json_response({"error": error}, status=500)
    
    # Start background poller
    asyncio.create_task(_background_poll(prompt_id))
    
    return web.json_response({"prompt_id": prompt_id, "status": "pending"})

async def _background_poll(prompt_id):
    """Background task to poll job and shutdown ComfyUI when done."""
    global comfyui_last_used
    img_path, error = await poll_job(prompt_id)
    if error:
        print(f"[server] Job {prompt_id}: {error}")
    else:
        print(f"[server] Job {prompt_id}: done → {img_path}")
    comfyui_last_used = time.time()

async def handle_status(request):
    """Check job status."""
    prompt_id = request.match_info["prompt_id"]
    job = active_jobs.get(prompt_id)
    if not job:
        return web.json_response({"error": "Unknown job"}, status=404)
    
    result = {
        "prompt_id": prompt_id,
        "status": job["status"],
        "elapsed": round(time.time() - job["start_time"], 1),
        "prompt": job["prompt"],
    }
    if job["image_path"]:
        result["image_url"] = f"/outputs/{Path(job['image_path']).name}"
    return web.json_response(result)

async def handle_output(request):
    """Serve generated images."""
    filename = request.match_info["filename"]
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return web.Response(status=404)
    return web.FileResponse(filepath)

async def handle_comfyui_status(request):
    """Check ComfyUI server status."""
    result = {"running": comfyui_ready, "pid": comfyui_process.pid if comfyui_process else None}
    if comfyui_ready:
        try:
            async with ClientSession() as s:
                async with s.get(f"http://127.0.0.1:{COMFYUI_PORT}/system_stats", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    stats = await r.json()
                    result["stats"] = stats.get("system", {})
        except Exception:
            pass
    return web.json_response(result)

async def handle_start_comfyui(request):
    """Manually start ComfyUI."""
    started = await start_comfyui()
    return web.json_response({"started": started})

async def handle_stop_comfyui(request):
    """Manually stop ComfyUI."""
    await stop_comfyui()
    return web.json_response({"stopped": True})

# ── Main ────────────────────────────────────────────────────────────

def main():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/workflows", handle_workflows)
    app.router.add_post("/api/generate", handle_generate)
    app.router.add_get("/api/status/{prompt_id}", handle_status)
    app.router.get("/outputs/{filename}", handle_output)
    app.router.add_get("/api/comfyui", handle_comfyui_status)
    app.router.add_post("/api/comfyui/start", handle_start_comfyui)
    app.router.add_post("/api/comfyui/stop", handle_stop_comfyui)
    
    # Serve outputs as static
    app.router.add_static("/outputs/", path=str(OUTPUT_DIR))
    
    print(f"[server] Image server running on http://0.0.0.0:{SERVER_PORT}")
    web.run_app(app, host="0.0.0.0", port=SERVER_PORT)

if __name__ == "__main__":
    main()

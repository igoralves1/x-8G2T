#!/usr/bin/env python3
"""
SPC Training Metrics Server
============================
Runs on the Windows HOST (not inside Docker) during training.

Reads:  output/metrics.json  (written every 5s by the training container)
Serves:
  GET /              → training-dashboard.html  (standalone browser dashboard)
  GET /api/metrics   → current metrics as JSON  (polling endpoint)
  GET /api/stream    → Server-Sent Events stream  (used by sm-dashboard-client)

Start:
  pip install fastapi uvicorn
  python metrics_server.py

Then open:  http://localhost:8765
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE          = Path(__file__).parent
METRICS_FILE  = HERE / "output" / "metrics.json"
PIPELINE_FILE = HERE / "output" / "pipeline.json"
BUILD_LOG     = HERE / "output" / "build_log.txt"
DASHBOARD     = HERE / "training-dashboard.html"
RUN_SCRIPT    = HERE / "run_training.py"
PORT          = 8765

# ── Training process state ─────────────────────────────────────────────────────
_training_proc: subprocess.Popen | None = None
_training_lock = Lock()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="SPC Training Metrics", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # localhost Vue dev server + any port
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _read_metrics() -> dict:
    """Read and return the latest metrics. Returns a safe default if not yet written."""
    try:
        if METRICS_FILE.exists():
            with open(METRICS_FILE, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "status": "idle",
        "phase": "waiting",
        "progress_pct": 0,
        "step": 0,
        "total_steps": 0,
        "epoch": 0,
        "total_epochs": 0,
        "loss": None,
        "learning_rate": None,
        "grad_norm": None,
        "samples_per_sec": None,
        "elapsed_seconds": 0,
        "eta_seconds": None,
        "gpu": {},
        "history": [],
        "dataset_pairs": None,
        "updated_at": None,
        "message": "Waiting for training to start...",
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def dashboard():
    """Serve the standalone training dashboard HTML."""
    if DASHBOARD.exists():
        return FileResponse(DASHBOARD, media_type="text/html")
    return JSONResponse(
        {"error": "training-dashboard.html not found", "metrics_url": "/api/metrics"},
        status_code=404,
    )


@app.get("/api/metrics")
async def metrics():
    """Current training metrics snapshot — poll this every 5 seconds."""
    return JSONResponse(_read_metrics())


@app.get("/api/pipeline")
async def pipeline():
    """Pipeline step status — which stage the training process is in."""
    try:
        if PIPELINE_FILE.exists():
            return JSONResponse(json.loads(PIPELINE_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return JSONResponse({"steps": [], "current_step": None, "current_status": None})


@app.get("/api/docker")
async def docker_info():
    """Docker images and containers relevant to spc-training."""
    try:
        # Images
        img_result = subprocess.run(
            ["docker", "images", "--format",
             '{"repo":"{{.Repository}}","tag":"{{.Tag}}","id":"{{.ID}}","size":"{{.Size}}","created":"{{.CreatedSince}}"}'],
            capture_output=True, text=True, timeout=5,
        )
        images = []
        for line in img_result.stdout.strip().splitlines():
            if line:
                try:
                    images.append(json.loads(line))
                except Exception:
                    pass

        # Containers — all, not filtered
        ctr_result = subprocess.run(
            ["docker", "ps", "-a", "--format",
             '{"id":"{{.ID}}","image":"{{.Image}}","status":"{{.Status}}","name":"{{.Names}}","created":"{{.CreatedAt}}"}'],
            capture_output=True, text=True, timeout=5,
        )
        containers = []
        for line in ctr_result.stdout.strip().splitlines():
            if line:
                try:
                    containers.append(json.loads(line))
                except Exception:
                    pass

        return JSONResponse({"images": images, "containers": containers})
    except Exception as e:
        return JSONResponse({"images": [], "containers": [], "error": str(e)})


@app.post("/api/start-training")
async def start_training():
    """Launch run_training.py as a background process on the Windows host."""
    global _training_proc
    with _training_lock:
        # Check if already running
        if _training_proc is not None and _training_proc.poll() is None:
            return JSONResponse({"ok": False, "error": "Training is already running.", "pid": _training_proc.pid}, status_code=409)

        if not RUN_SCRIPT.exists():
            return JSONResponse({"ok": False, "error": f"run_training.py not found at {RUN_SCRIPT}"}, status_code=404)

        # Clear stale output from previous run
        for stale in ["metrics.json", "pipeline.json"]:
            p = HERE / "output" / stale
            if p.exists():
                p.unlink()

        try:
            _training_proc = subprocess.Popen(
                [sys.executable, str(RUN_SCRIPT)],
                cwd=str(HERE),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                # Detach from this server process so it survives independently
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            return JSONResponse({"ok": True, "pid": _training_proc.pid, "message": f"Training started (PID {_training_proc.pid})"})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/stop-training")
async def stop_training():
    """Kill the training process tree (run_training.py + all Docker children)."""
    global _training_proc
    killed = []
    errors = []

    with _training_lock:
        if _training_proc is not None and _training_proc.poll() is None:
            pid = _training_proc.pid
            try:
                if os.name == "nt":
                    # Windows: kill entire process tree via taskkill
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                                   capture_output=True)
                else:
                    import signal, os as _os
                    _os.killpg(_os.getpgid(pid), signal.SIGTERM)
                killed.append(f"run_training.py (PID {pid})")
            except Exception as e:
                errors.append(str(e))
            _training_proc = None

    # Also stop any running spc-training Docker containers
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", "name=spc-training"],
            capture_output=True, text=True, timeout=5,
        )
        container_ids = result.stdout.strip().splitlines()
        for cid in container_ids:
            subprocess.run(["docker", "stop", cid], capture_output=True, timeout=30)
            killed.append(f"docker container {cid[:12]}")
    except Exception as e:
        errors.append(f"docker stop: {e}")

    if killed:
        return JSONResponse({"ok": True, "killed": killed, "errors": errors})
    return JSONResponse({"ok": False, "error": "Nothing was running.", "errors": errors}, status_code=409)


@app.get("/api/training-process")
async def training_process():
    """Return whether a training process is currently running."""
    global _training_proc
    running = _training_proc is not None and _training_proc.poll() is None
    pid = _training_proc.pid if running else None
    return JSONResponse({"running": running, "pid": pid})


@app.get("/api/log")
async def build_log(tail: int = 80):
    """Last N lines of the Docker build / container run log."""
    try:
        if BUILD_LOG.exists():
            lines = BUILD_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            return JSONResponse({"lines": lines[-tail:], "total": len(lines)})
    except Exception as e:
        return JSONResponse({"lines": [], "total": 0, "error": str(e)})
    return JSONResponse({"lines": [], "total": 0})


@app.get("/api/stream")
async def stream():
    """
    Server-Sent Events stream — pushed every 5 seconds.
    Used by sm-dashboard-client for live chart updates.

    EventSource usage in Vue/JS:
        const es = new EventSource('http://localhost:8765/api/stream')
        es.onmessage = (e) => { const m = JSON.parse(e.data); ... }
    """
    async def event_generator():
        last_ts = None
        while True:
            data = _read_metrics()
            ts = data.get("updated_at")
            # Only push if data changed (or first message)
            if ts != last_ts:
                last_ts = ts
                payload = json.dumps(data)
                yield f"data: {payload}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  SPC Training Metrics Server")
    print(f"{'='*60}")
    print(f"  Dashboard  : http://localhost:{PORT}")
    print(f"  API        : http://localhost:{PORT}/api/metrics")
    print(f"  SSE stream : http://localhost:{PORT}/api/stream")
    print(f"  Metrics file: {METRICS_FILE}")
    print(f"{'='*60}\n")

    if not METRICS_FILE.parent.exists():
        METRICS_FILE.parent.mkdir(parents=True)
        print(f"  Created output dir: {METRICS_FILE.parent}")

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
